# Planning Agent with Aggressive Multi-Article Clustering
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import numpy as np
import logging

from app.agents.base_agent import BaseAgent
from app.models.schemas import (
    ComprehensionResult,
    TagResult,
    ArticlePlan,
    ArticleSection,
    CrawlResult,
    PostData,
)
from app.services.embedding_service import EmbeddingService


class PlanningAgent(BaseAgent):
    """
    Multi-article planning agent that clusters posts semantically using BERT embeddings
    and generates MULTIPLE ArticlePlans when content diversity exists.
    
    CRITICAL RULES:
    - Each post is treated as an independent knowledge unit
    - Multiple articles are REQUIRED when content diversity exists
    - Single article ONLY allowed if: posts <= 2 OR similarity >= 0.9
    - NEVER collapse all posts into one article by default
    - NEVER use page/group name as article topic
    """
    
    # Clustering parameters - tuned for aggressive multi-article generation
    MIN_POSTS_PER_CLUSTER = 2
    MAX_ARTICLES = 15
    MIN_POSTS_FOR_MULTI_ARTICLE = 3
    
    # DBSCAN parameters - LOW eps to create MORE clusters
    INITIAL_EPS = 0.35  # Start with low threshold for more clusters
    MIN_EPS = 0.15      # Minimum threshold
    MAX_EPS = 0.60      # Maximum threshold
    EPS_STEP = 0.05     # Step for threshold adjustment
    
    # Similarity thresholds
    SINGLE_ARTICLE_SIMILARITY_THRESHOLD = 0.9  # Only allow single article if ALL posts are this similar
    
    def __init__(self):
        super().__init__("PlanningAgent")
        self.embedding_service = EmbeddingService()
        self.logger = logging.getLogger("planning_agent")

    async def execute(
        self,
        crawl_result: CrawlResult,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> List[ArticlePlan]:
        """
        Main execution: clusters posts semantically and returns MULTIPLE article plans.
        Uses DBSCAN clustering with automatic threshold adjustment.
        
        GUARANTEES:
        - Returns multiple ArticlePlans when content diversity exists
        - Single ArticlePlan only if posts <= 2 or all posts have similarity >= 0.9
        """
        n_posts = len(comprehension_results)
        self.log_info(f"Planning articles from {n_posts} posts using DBSCAN clustering")

        # Edge case: too few posts for multi-article
        if n_posts < self.MIN_POSTS_FOR_MULTI_ARTICLE:
            self.log_info(f"Only {n_posts} posts - insufficient for multi-article (threshold: {self.MIN_POSTS_FOR_MULTI_ARTICLE})")
            plan = self._create_single_plan(crawl_result, comprehension_results, tag_results)
            return [plan]

        # Generate embeddings for all posts
        post_texts = self._get_post_texts(crawl_result, comprehension_results)
        self.log_info("Generating embeddings for semantic clustering")
        embeddings = self.embedding_service.get_embeddings(post_texts)
        
        if len(embeddings) == 0:
            self.log_warning("No embeddings generated - falling back to single article")
            plan = self._create_single_plan(crawl_result, comprehension_results, tag_results)
            return [plan]
        
        # Compute similarity matrix
        similarity_matrix = self.embedding_service.compute_similarity_matrix(embeddings)
        
        # Check if ALL posts are extremely similar (single article condition)
        avg_similarity = self._compute_average_similarity(similarity_matrix)
        min_similarity = self._compute_min_similarity(similarity_matrix)
        
        self.log_info(f"Similarity stats: avg={avg_similarity:.3f}, min={min_similarity:.3f}")
        
        if min_similarity >= self.SINGLE_ARTICLE_SIMILARITY_THRESHOLD:
            self.log_info(f"All posts have similarity >= {self.SINGLE_ARTICLE_SIMILARITY_THRESHOLD} - single article justified")
            plan = self._create_single_plan(crawl_result, comprehension_results, tag_results)
            return [plan]
        
        # Run DBSCAN clustering with automatic threshold adjustment
        clusters = self._run_adaptive_dbscan(embeddings, comprehension_results, tag_results)
        
        if len(clusters) == 0:
            self.log_warning("DBSCAN produced no valid clusters - using topic-based fallback")
            clusters = self._fallback_topic_clustering(comprehension_results, tag_results)
        
        # CRITICAL: If we still have only 1 cluster but similarity is low, FORCE split
        if len(clusters) <= 1 and min_similarity < self.SINGLE_ARTICLE_SIMILARITY_THRESHOLD:
            self.log_warning(f"Only {len(clusters)} cluster(s) but min_similarity={min_similarity:.3f} < {self.SINGLE_ARTICLE_SIMILARITY_THRESHOLD}")
            self.log_info("FORCING split using k-means based approach")
            clusters = self._force_multiple_clusters(embeddings, comprehension_results, tag_results, n_posts)
        
        # Create article plans from clusters
        article_plans = []
        for cluster_name, post_ids in clusters.items():
            if len(post_ids) < self.MIN_POSTS_PER_CLUSTER:
                continue
                
            cluster_comprehensions = [
                c for c in comprehension_results if c.post_id in post_ids
            ]
            cluster_tags = [
                t for t in tag_results if t.post_id in post_ids
            ]
            
            plan = self._create_cluster_plan(
                cluster_name,
                post_ids,
                cluster_comprehensions,
                cluster_tags,
                crawl_result,
            )
            article_plans.append(plan)
            
            if len(article_plans) >= self.MAX_ARTICLES:
                break

        # Safety: if no plans were created, create single plan with explicit logging
        if len(article_plans) == 0:
            self.log_warning("SAFETY FALLBACK: No article plans created - creating single article")
            plan = self._create_single_plan(crawl_result, comprehension_results, tag_results)
            article_plans = [plan]
        
        self.log_info(f"RESULT: Created {len(article_plans)} article plans from {n_posts} posts")
        
        # ASSERTION: Log explicit warning if single article from many posts
        if len(article_plans) == 1 and n_posts >= self.MIN_POSTS_FOR_MULTI_ARTICLE:
            self.log_warning(
                f"ATTENTION: Single article from {n_posts} posts. "
                f"Similarity: avg={avg_similarity:.3f}, min={min_similarity:.3f}. "
                f"This should only happen if all posts are nearly identical."
            )
        
        return article_plans


    def _compute_average_similarity(self, similarity_matrix: np.ndarray) -> float:
        """Compute average pairwise similarity (excluding diagonal)."""
        n = len(similarity_matrix)
        if n <= 1:
            return 1.0
        
        # Get upper triangle without diagonal
        upper_triangle = np.triu(similarity_matrix, k=1)
        n_pairs = (n * (n - 1)) // 2
        return float(np.sum(upper_triangle) / n_pairs) if n_pairs > 0 else 1.0

    def _compute_min_similarity(self, similarity_matrix: np.ndarray) -> float:
        """Compute minimum pairwise similarity (excluding diagonal)."""
        n = len(similarity_matrix)
        if n <= 1:
            return 1.0
        
        # Set diagonal to 1.0 (self-similarity) then find min of off-diagonal
        sim_copy = similarity_matrix.copy()
        np.fill_diagonal(sim_copy, 1.0)
        
        # Get minimum from upper triangle
        min_val = 1.0
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i, j] < min_val:
                    min_val = similarity_matrix[i, j]
        
        return float(min_val)

    def _run_adaptive_dbscan(
        self,
        embeddings: np.ndarray,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> Dict[str, List[str]]:
        """
        Run DBSCAN with adaptive eps parameter to ensure multiple clusters.
        Starts with low eps and increases if too many noise points.
        """
        from sklearn.cluster import DBSCAN
        from sklearn.metrics.pairwise import cosine_distances
        
        # Convert to distance matrix (DBSCAN uses distance, not similarity)
        distance_matrix = cosine_distances(embeddings)
        
        best_clusters = {}
        best_n_clusters = 0
        best_eps = self.INITIAL_EPS
        
        # Try different eps values to find optimal clustering
        current_eps = self.INITIAL_EPS
        
        while current_eps <= self.MAX_EPS:
            clustering = DBSCAN(
                eps=current_eps,
                min_samples=self.MIN_POSTS_PER_CLUSTER,
                metric='precomputed'
            ).fit(distance_matrix)
            
            labels = clustering.labels_
            unique_labels = set(labels)
            unique_labels.discard(-1)  # Remove noise label
            n_clusters = len(unique_labels)
            n_noise = list(labels).count(-1)
            
            self.log_info(f"DBSCAN eps={current_eps:.2f}: {n_clusters} clusters, {n_noise} noise points")
            
            # Track best result (most clusters with acceptable noise)
            if n_clusters > best_n_clusters and n_noise < len(embeddings) * 0.5:
                best_n_clusters = n_clusters
                best_eps = current_eps
                best_clusters = self._labels_to_clusters(
                    labels, 
                    comprehension_results, 
                    tag_results
                )
            
            # If we have multiple clusters, we're done
            if n_clusters >= 2:
                self.log_info(f"Found {n_clusters} clusters at eps={current_eps:.2f}")
                return self._labels_to_clusters(labels, comprehension_results, tag_results)
            
            # Try lower eps for more clusters
            current_eps -= self.EPS_STEP
            if current_eps < self.MIN_EPS:
                break
        
        # If low eps didn't work, try higher eps to reduce noise
        current_eps = self.INITIAL_EPS + self.EPS_STEP
        while current_eps <= self.MAX_EPS:
            clustering = DBSCAN(
                eps=current_eps,
                min_samples=self.MIN_POSTS_PER_CLUSTER,
                metric='precomputed'
            ).fit(distance_matrix)
            
            labels = clustering.labels_
            unique_labels = set(labels)
            unique_labels.discard(-1)
            n_clusters = len(unique_labels)
            n_noise = list(labels).count(-1)
            
            self.log_info(f"DBSCAN eps={current_eps:.2f}: {n_clusters} clusters, {n_noise} noise points")
            
            if n_clusters > best_n_clusters:
                best_n_clusters = n_clusters
                best_eps = current_eps
                best_clusters = self._labels_to_clusters(
                    labels, 
                    comprehension_results, 
                    tag_results
                )
            
            if n_clusters >= 2:
                return self._labels_to_clusters(labels, comprehension_results, tag_results)
            
            current_eps += self.EPS_STEP
        
        self.log_info(f"Best DBSCAN result: {best_n_clusters} clusters at eps={best_eps:.2f}")
        return best_clusters

    def _labels_to_clusters(
        self,
        labels: np.ndarray,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> Dict[str, List[str]]:
        """Convert DBSCAN labels to named clusters."""
        tag_map = {tr.post_id: tr for tr in tag_results}
        clusters: Dict[int, List[int]] = defaultdict(list)
        noise_posts: List[int] = []
        
        for idx, label in enumerate(labels):
            if label == -1:
                noise_posts.append(idx)
            else:
                clusters[label].append(idx)
        
        # Assign noise points to nearest cluster
        if noise_posts and clusters:
            # For now, add noise to largest cluster (can be improved)
            largest_cluster = max(clusters.keys(), key=lambda k: len(clusters[k]))
            clusters[largest_cluster].extend(noise_posts)
        elif noise_posts and not clusters:
            # All points are noise - create one cluster from all
            clusters[0] = noise_posts
        
        # Name clusters based on content
        named_clusters: Dict[str, List[str]] = {}
        for cluster_id, post_indices in clusters.items():
            post_ids = [comprehension_results[i].post_id for i in post_indices]
            cluster_comps = [comprehension_results[i] for i in post_indices]
            cluster_tags = [tag_map.get(pid) for pid in post_ids if pid in tag_map]
            
            cluster_name = self._generate_cluster_name(cluster_comps, cluster_tags)
            
            # Ensure unique names
            if cluster_name in named_clusters:
                cluster_name = f"{cluster_name} ({cluster_id + 1})"
            
            named_clusters[cluster_name] = post_ids
        
        return named_clusters

    def _force_multiple_clusters(
        self,
        embeddings: np.ndarray,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
        n_posts: int,
    ) -> Dict[str, List[str]]:
        """
        FORCE creation of multiple clusters when DBSCAN fails but content is diverse.
        Uses K-means with k = max(2, n_posts // 3).
        """
        from sklearn.cluster import KMeans
        
        # Determine number of clusters: at least 2, at most n_posts // 2
        n_clusters = max(2, min(n_posts // 3, 5))
        
        self.log_info(f"Forcing {n_clusters} clusters using K-means")
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        return self._labels_to_clusters(labels, comprehension_results, tag_results)

    def _fallback_topic_clustering(
        self,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> Dict[str, List[str]]:
        """
        Fallback clustering using topics and entities when embedding clustering fails.
        MUST produce multiple clusters if content is diverse.
        """
        tag_map = {tr.post_id: tr for tr in tag_results}
        topic_clusters: Dict[str, List[str]] = defaultdict(list)
        
        for comp in comprehension_results:
            post_id = comp.post_id
            tag_result = tag_map.get(post_id)
            
            # Determine primary topic - be more aggressive about splitting
            primary_topic = self._determine_primary_topic(comp, tag_result)
            topic_clusters[primary_topic].append(post_id)
        
        # DON'T merge aggressively - keep clusters separate
        final_clusters: Dict[str, List[str]] = {}
        orphan_posts: List[str] = []
        
        for topic, post_ids in topic_clusters.items():
            if len(post_ids) >= self.MIN_POSTS_PER_CLUSTER:
                final_clusters[topic] = post_ids
            else:
                orphan_posts.extend(post_ids)
        
        # Handle orphans: create "Miscellaneous" cluster if enough
        if len(orphan_posts) >= self.MIN_POSTS_PER_CLUSTER:
            final_clusters["Miscellaneous Topics"] = orphan_posts
        elif orphan_posts and final_clusters:
            # Add to smallest cluster to balance
            smallest_cluster = min(final_clusters.keys(), key=lambda k: len(final_clusters[k]))
            final_clusters[smallest_cluster].extend(orphan_posts)
        
        return final_clusters

    def _get_post_texts(
        self,
        crawl_result: CrawlResult,
        comprehension_results: List[ComprehensionResult],
    ) -> List[str]:
        """Extract text content from posts for embedding."""
        post_map = {p.post_id: p for p in crawl_result.posts}
        texts = []
        
        for comp in comprehension_results:
            post = post_map.get(comp.post_id)
            if post:
                # Combine content with extracted features for richer embedding
                text_parts = [post.content[:1500]]
                text_parts.extend(comp.topics[:5])
                text_parts.extend(comp.keywords[:10])
                for entity in comp.entities[:5]:
                    text_parts.append(entity.text)
                texts.append(" ".join(text_parts))
            else:
                texts.append("")
        
        return texts

    def _generate_cluster_name(
        self,
        comprehensions: List[ComprehensionResult],
        tag_results: List[Optional[TagResult]],
    ) -> str:
        """Generate a meaningful cluster name from post content. NEVER use page name."""
        # Priority 1: Named entities
        entity_counter = Counter()
        for comp in comprehensions:
            for entity in comp.entities:
                if entity.label in ["PERSON", "ORG", "EVENT", "PRODUCT", "WORK_OF_ART", "GPE"]:
                    entity_counter[entity.text] += 1
        
        if entity_counter:
            most_common = entity_counter.most_common(1)[0][0]
            return most_common
        
        # Priority 2: Topics
        topic_counter = Counter()
        for comp in comprehensions:
            for topic in comp.topics:
                topic_counter[topic] += 1
        
        if topic_counter:
            most_common = topic_counter.most_common(1)[0][0]
            return most_common.title()
        
        # Priority 3: Categories
        category_counter = Counter()
        for tag in tag_results:
            if tag:
                for cat in tag.categories:
                    category_counter[cat] += 1
        
        if category_counter:
            most_common = category_counter.most_common(1)[0][0]
            return most_common.title()
        
        # Priority 4: Keywords
        keyword_counter = Counter()
        for comp in comprehensions:
            for kw in comp.keywords[:5]:
                keyword_counter[kw] += 1
        
        if keyword_counter:
            most_common = keyword_counter.most_common(1)[0][0]
            return most_common.title()
        
        return "General Content"

    def _determine_primary_topic(
        self,
        comp: ComprehensionResult,
        tag_result: Optional[TagResult],
    ) -> str:
        """Determine the primary topic for a single post."""
        # Priority: Named entities > Topics > Categories > Keywords
        important_entities = [
            e.text for e in comp.entities 
            if e.label in ["PERSON", "ORG", "EVENT", "PRODUCT", "WORK_OF_ART"]
        ]
        if important_entities:
            return important_entities[0]

        if comp.topics and len(comp.topics) > 0:
            return comp.topics[0]

        if tag_result and tag_result.categories:
            return tag_result.categories[0]
        
        if comp.keywords:
            return comp.keywords[0]

        return "general"

    def _create_cluster_plan(
        self,
        cluster_name: str,
        post_ids: List[str],
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
        crawl_result: CrawlResult,
    ) -> ArticlePlan:
        """Create an article plan for a specific topic cluster."""
        dominant_language = self._determine_dominant_language(comprehension_results)
        dominant_dialect = self._determine_dominant_dialect(comprehension_results)

        title = self._generate_cluster_title(
            cluster_name,
            comprehension_results,
            dominant_language,
        )

        summary = self._generate_cluster_summary(
            cluster_name,
            comprehension_results,
            tag_results,
        )

        sections = self._create_cluster_sections(
            post_ids,
            comprehension_results,
            dominant_language,
        )

        return ArticlePlan(
            title=title,
            summary=summary,
            sections=sections,
            language=dominant_language,
            dialect=dominant_dialect,
        )

    def _create_single_plan(
        self,
        crawl_result: CrawlResult,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> ArticlePlan:
        """Create a single plan. ONLY used when legitimately justified."""
        self.log_info("Creating single article plan (justified by low post count or high similarity)")
        
        dominant_language = self._determine_dominant_language(comprehension_results)
        dominant_dialect = self._determine_dominant_dialect(comprehension_results)

        title = self._generate_content_based_title(comprehension_results, dominant_language)
        summary = self._generate_content_summary(comprehension_results, tag_results)
        post_ids = [c.post_id for c in comprehension_results]
        sections = self._create_cluster_sections(post_ids, comprehension_results, dominant_language)

        return ArticlePlan(
            title=title,
            summary=summary,
            sections=sections,
            language=dominant_language,
            dialect=dominant_dialect,
        )

    def _generate_cluster_title(
        self,
        cluster_name: str,
        comprehension_results: List[ComprehensionResult],
        language: str,
    ) -> str:
        """Generate a title based on the cluster topic."""
        if cluster_name and cluster_name.lower() not in ["general", "miscellaneous", "general content", "miscellaneous topics"]:
            return cluster_name.title() if cluster_name.isascii() else cluster_name

        all_entities = []
        for comp in comprehension_results:
            for entity in comp.entities:
                if entity.label in ["PERSON", "ORG", "EVENT", "GPE", "PRODUCT"]:
                    all_entities.append(entity.text)
        
        if all_entities:
            most_common = Counter(all_entities).most_common(1)
            if most_common:
                return most_common[0][0]

        all_topics = []
        for comp in comprehension_results:
            all_topics.extend(comp.topics)
        
        if all_topics:
            most_common = Counter(all_topics).most_common(1)
            if most_common:
                return most_common[0][0].title()

        if language == "ar":
            return "موضوع عام"
        return "General Topic"

    def _generate_content_based_title(
        self,
        comprehension_results: List[ComprehensionResult],
        language: str,
    ) -> str:
        """Generate title based on post content, NOT page name."""
        all_entities = []
        for comp in comprehension_results:
            for entity in comp.entities:
                if entity.label in ["PERSON", "ORG", "EVENT", "PRODUCT", "GPE"]:
                    all_entities.append(entity.text)
        
        if all_entities:
            most_common = Counter(all_entities).most_common(1)
            if most_common:
                return most_common[0][0]

        all_topics = []
        for comp in comprehension_results:
            all_topics.extend(comp.topics)
        
        if all_topics:
            most_common = Counter(all_topics).most_common(1)
            if most_common:
                return most_common[0][0].title()

        all_keywords = []
        for comp in comprehension_results:
            all_keywords.extend(comp.keywords[:3])
        
        if all_keywords:
            most_common = Counter(all_keywords).most_common(2)
            return " ".join([kw for kw, _ in most_common]).title()

        if language == "ar":
            return "محتوى متنوع"
        return "Aggregated Content"

    def _generate_cluster_summary(
        self,
        cluster_name: str,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> str:
        """Generate summary for a topic cluster."""
        all_keywords = []
        for comp in comprehension_results:
            all_keywords.extend(comp.keywords[:5])

        top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(5)]
        
        if top_keywords:
            return f"Content covering: {', '.join(top_keywords)}"
        
        if cluster_name and cluster_name.lower() not in ["general", "miscellaneous", "general content"]:
            return f"Information about {cluster_name}"
        
        return f"Article compiled from {len(comprehension_results)} sources"

    def _generate_content_summary(
        self,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> str:
        """Generate summary based on post content."""
        all_keywords = []
        for comp in comprehension_results:
            all_keywords.extend(comp.keywords[:5])

        top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(5)]
        
        if top_keywords:
            return f"Content related to: {', '.join(top_keywords)}"
        
        return f"Article compiled from {len(comprehension_results)} posts"

    def _create_cluster_sections(
        self,
        post_ids: List[str],
        comprehension_results: List[ComprehensionResult],
        language: str,
    ) -> List[ArticleSection]:
        """Create sections for a cluster's article."""
        sections = []
        lang_key = "ar" if language == "ar" else "en"

        section_titles = {
            "introduction": {"en": "Introduction", "ar": "مقدمة"},
            "details": {"en": "Details", "ar": "التفاصيل"},
            "context": {"en": "Context", "ar": "السياق"},
        }

        sections.append(
            ArticleSection(
                title=section_titles["introduction"][lang_key],
                content_sources=[],
                order=0,
            )
        )

        sections.append(
            ArticleSection(
                title=section_titles["details"][lang_key],
                content_sources=post_ids,
                order=1,
            )
        )

        if len(post_ids) > 3:
            sections.append(
                ArticleSection(
                    title=section_titles["context"][lang_key],
                    content_sources=post_ids[:2],
                    order=2,
                )
            )

        return sections

    def _determine_dominant_language(
        self, comprehension_results: List[ComprehensionResult]
    ) -> str:
        language_counts: Dict[str, float] = defaultdict(float)

        for result in comprehension_results:
            lang = result.language_info.language
            confidence = result.language_info.confidence
            language_counts[lang] += confidence

        if not language_counts:
            return "en"

        return max(language_counts, key=language_counts.get)

    def _determine_dominant_dialect(
        self, comprehension_results: List[ComprehensionResult]
    ) -> Optional[str]:
        dialect_counts: Dict[str, int] = defaultdict(int)

        for result in comprehension_results:
            dialect = result.language_info.dialect
            if dialect:
                dialect_counts[dialect] += 1

        if not dialect_counts:
            return None

        return max(dialect_counts, key=dialect_counts.get)
