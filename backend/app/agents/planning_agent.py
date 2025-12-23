# Planning Agent with Semantic Clustering
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import numpy as np

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
    and generates multiple ArticlePlans for diverse content.
    
    CRITICAL: This agent must generate multiple articles when content is diverse.
    Page/group itself must NEVER be the main article topic.
    """
    
    MIN_POSTS_PER_CLUSTER = 2
    MAX_ARTICLES = 10
    MIN_POSTS_FOR_MULTI_ARTICLE = 3
    SIMILARITY_THRESHOLD = 0.75  # Posts more similar than this go in same cluster
    MIN_CLUSTER_SEPARATION = 0.5  # Clusters must be at least this different
    
    def __init__(self):
        super().__init__("PlanningAgent")
        self.embedding_service = EmbeddingService()

    async def execute(
        self,
        crawl_result: CrawlResult,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> List[ArticlePlan]:
        """
        Main execution: clusters posts semantically and returns MULTIPLE article plans.
        Uses BERT embeddings for understanding post relationships.
        """
        self.log_info(f"Planning articles from {len(comprehension_results)} posts using semantic clustering")

        if len(comprehension_results) < self.MIN_POSTS_FOR_MULTI_ARTICLE:
            plan = self._create_single_plan(crawl_result, comprehension_results, tag_results)
            self.log_info("Created 1 article plan (insufficient posts for clustering)")
            return [plan]

        # Get post texts for embedding
        post_id_to_idx = {c.post_id: idx for idx, c in enumerate(comprehension_results)}
        post_texts = self._get_post_texts(crawl_result, comprehension_results)
        
        # Generate embeddings
        self.log_info("Generating embeddings for semantic clustering")
        embeddings = self.embedding_service.get_embeddings(post_texts)
        
        # Perform semantic clustering
        clusters = self._semantic_cluster_posts(
            embeddings, 
            comprehension_results, 
            tag_results
        )
        
        if len(clusters) == 0:
            plan = self._create_single_plan(crawl_result, comprehension_results, tag_results)
            return [plan]

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

        if len(article_plans) == 0:
            plan = self._create_single_plan(crawl_result, comprehension_results, tag_results)
            article_plans = [plan]

        self.log_info(f"Created {len(article_plans)} article plans from semantic clusters")
        return article_plans

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
                # Combine post content with extracted topics and keywords for richer embedding
                text_parts = [post.content[:1500]]
                text_parts.extend(comp.topics[:5])
                text_parts.extend(comp.keywords[:10])
                texts.append(" ".join(text_parts))
            else:
                texts.append("")
        
        return texts

    def _semantic_cluster_posts(
        self,
        embeddings: np.ndarray,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> Dict[str, List[str]]:
        """
        Cluster posts semantically using embeddings and hierarchical approach.
        Returns dict mapping cluster name to list of post IDs.
        """
        if len(embeddings) == 0:
            return {}
        
        # Compute similarity matrix
        similarity_matrix = self.embedding_service.compute_similarity_matrix(embeddings)
        
        # Use agglomerative clustering approach
        n_posts = len(comprehension_results)
        post_ids = [c.post_id for c in comprehension_results]
        
        # Initialize: each post in its own cluster
        cluster_assignments = list(range(n_posts))
        
        # Merge similar posts into clusters
        for i in range(n_posts):
            for j in range(i + 1, n_posts):
                if similarity_matrix[i, j] >= self.SIMILARITY_THRESHOLD:
                    # Merge clusters
                    old_cluster = cluster_assignments[j]
                    new_cluster = cluster_assignments[i]
                    for k in range(n_posts):
                        if cluster_assignments[k] == old_cluster:
                            cluster_assignments[k] = new_cluster
        
        # Group posts by cluster assignment
        raw_clusters: Dict[int, List[int]] = defaultdict(list)
        for idx, cluster_id in enumerate(cluster_assignments):
            raw_clusters[cluster_id].append(idx)
        
        # Filter and name clusters
        tag_map = {tr.post_id: tr for tr in tag_results}
        named_clusters: Dict[str, List[str]] = {}
        
        for cluster_id, post_indices in raw_clusters.items():
            if len(post_indices) < self.MIN_POSTS_PER_CLUSTER:
                continue
            
            cluster_post_ids = [post_ids[i] for i in post_indices]
            cluster_comps = [comprehension_results[i] for i in post_indices]
            cluster_tags_list = [tag_map.get(pid) for pid in cluster_post_ids if pid in tag_map]
            
            # Generate cluster name from content (NOT page name)
            cluster_name = self._generate_cluster_name(cluster_comps, cluster_tags_list)
            
            # Ensure unique cluster names
            if cluster_name in named_clusters:
                cluster_name = f"{cluster_name} ({len(named_clusters) + 1})"
            
            named_clusters[cluster_name] = cluster_post_ids
        
        # If diversity is low (all posts very similar), still try to split by topic
        if len(named_clusters) <= 1 and n_posts >= 4:
            named_clusters = self._fallback_topic_clustering(
                comprehension_results, 
                tag_results
            )
        
        return named_clusters

    def _generate_cluster_name(
        self,
        comprehensions: List[ComprehensionResult],
        tag_results: List[Optional[TagResult]],
    ) -> str:
        """Generate a meaningful cluster name from post content."""
        # Collect all important entities
        entity_counter = Counter()
        for comp in comprehensions:
            for entity in comp.entities:
                if entity.label in ["PERSON", "ORG", "EVENT", "PRODUCT", "WORK_OF_ART", "GPE"]:
                    entity_counter[entity.text] += 1
        
        # Use most common entity as cluster name
        if entity_counter:
            most_common = entity_counter.most_common(1)[0][0]
            return most_common
        
        # Fall back to topics
        topic_counter = Counter()
        for comp in comprehensions:
            for topic in comp.topics:
                topic_counter[topic] += 1
        
        if topic_counter:
            most_common = topic_counter.most_common(1)[0][0]
            return most_common.title()
        
        # Fall back to categories
        category_counter = Counter()
        for tag in tag_results:
            if tag:
                for cat in tag.categories:
                    category_counter[cat] += 1
        
        if category_counter:
            most_common = category_counter.most_common(1)[0][0]
            return most_common.title()
        
        return "General Content"

    def _fallback_topic_clustering(
        self,
        comprehension_results: List[ComprehensionResult],
        tag_results: List[TagResult],
    ) -> Dict[str, List[str]]:
        """
        Fallback clustering using topics and categories when semantic clustering
        produces too few clusters.
        """
        tag_map = {tr.post_id: tr for tr in tag_results}
        topic_clusters: Dict[str, List[str]] = defaultdict(list)
        
        for comp in comprehension_results:
            post_id = comp.post_id
            tag_result = tag_map.get(post_id)
            
            # Determine primary topic
            primary_topic = self._determine_primary_topic(comp, tag_result)
            topic_clusters[primary_topic].append(post_id)
        
        # Merge small clusters
        return self._merge_small_clusters(topic_clusters)

    def _determine_primary_topic(
        self,
        comp: ComprehensionResult,
        tag_result: Optional[TagResult],
    ) -> str:
        """Determine the primary topic for a single post."""
        # Priority: Named entities > Topics > Categories
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

        return "general"

    def _merge_small_clusters(
        self,
        clusters: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """Merge clusters with too few posts."""
        merged: Dict[str, List[str]] = {}
        small_cluster_posts: List[str] = []
        
        for topic, post_ids in clusters.items():
            if len(post_ids) < self.MIN_POSTS_PER_CLUSTER:
                small_cluster_posts.extend(post_ids)
            else:
                merged[topic] = post_ids.copy()

        if small_cluster_posts and len(small_cluster_posts) >= self.MIN_POSTS_PER_CLUSTER:
            merged["Miscellaneous"] = small_cluster_posts
        elif small_cluster_posts and merged:
            largest_cluster = max(merged.keys(), key=lambda k: len(merged[k]))
            merged[largest_cluster].extend(small_cluster_posts)

        return merged

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
        """Fallback: create a single plan when clustering is not possible."""
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
        if cluster_name and cluster_name.lower() not in ["general", "miscellaneous", "general content"]:
            return cluster_name.title()

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
        
        if cluster_name and cluster_name.lower() not in ["general", "miscellaneous"]:
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
