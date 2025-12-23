# Generation Agent using Groq API
from typing import List, Dict

from app.agents.base_agent import BaseAgent
from app.models.schemas import (
    ArticlePlan,
    ArticleContent,
    CrawlResult,
    ComprehensionResult,
    PostData,
)
from app.services.groq_service import GroqService


class GenerationAgent(BaseAgent):
    """
    Multi-article generation agent that creates one article per ArticlePlan.
    Uses Groq API with open-weight LLMs for text generation.
    """
    
    def __init__(self):
        super().__init__("GenerationAgent")
        self.groq_service = GroqService()

    async def execute(
        self,
        article_plans: List[ArticlePlan],
        crawl_result: CrawlResult,
        comprehension_results: List[ComprehensionResult],
        feedback: str = None,
    ) -> List[ArticleContent]:
        """
        Generate MULTIPLE articles, one per ArticlePlan.
        Returns List[ArticleContent].
        """
        self.log_info(f"Generating {len(article_plans)} articles using Groq")

        post_map = {post.post_id: post for post in crawl_result.posts}
        comp_map = {comp.post_id: comp for comp in comprehension_results}

        generated_articles: List[ArticleContent] = []

        for idx, plan in enumerate(article_plans):
            self.log_info(f"Generating article {idx + 1}/{len(article_plans)}: {plan.title}")
            
            plan_post_ids = self._get_plan_post_ids(plan)
            
            if plan_post_ids:
                relevant_posts = {
                    pid: post_map[pid] 
                    for pid in plan_post_ids 
                    if pid in post_map
                }
            else:
                relevant_posts = post_map

            source_content = self._prepare_source_content(relevant_posts)

            prompt = self._build_generation_prompt(
                plan,
                source_content,
                feedback if idx == 0 else None,
            )

            generated_text = await self.groq_service.generate_with_retry(prompt)

            article_content = self._parse_generated_content(
                generated_text,
                plan,
            )

            generated_articles.append(article_content)

        self.log_info(f"Generated {len(generated_articles)} articles successfully")
        return generated_articles

    async def execute_single(
        self,
        article_plan: ArticlePlan,
        crawl_result: CrawlResult,
        comprehension_results: List[ComprehensionResult],
        feedback: str = None,
    ) -> ArticleContent:
        """
        Generate a single article (backward compatibility).
        """
        results = await self.execute(
            [article_plan],
            crawl_result,
            comprehension_results,
            feedback,
        )
        return results[0] if results else None

    def _get_plan_post_ids(self, plan: ArticlePlan) -> List[str]:
        """Extract all post IDs from an article plan's sections."""
        post_ids = []
        for section in plan.sections:
            post_ids.extend(section.content_sources)
        return list(set(post_ids))

    def _prepare_source_content(self, post_map: Dict[str, PostData]) -> str:
        content_parts = []

        for post_id, post in post_map.items():
            content_parts.append(f"[Post {post_id}]\n{post.content}\n")

        return "\n---\n".join(content_parts)

    def _build_generation_prompt(
        self,
        article_plan: ArticlePlan,
        source_content: str,
        feedback: str = None,
    ) -> str:
        language_instruction = self._get_language_instruction(
            article_plan.language,
            article_plan.dialect,
        )

        sections_list = "\n".join(
            f"- {section.title}" for section in article_plan.sections
        )

        prompt = f"""You are an expert encyclopedic writer. Transform the following social media posts into a high-quality, encyclopedic article about the TOPIC described below.

{language_instruction}

ARTICLE TOPIC/TITLE: {article_plan.title}

ARTICLE SUMMARY: {article_plan.summary}

REQUIRED SECTIONS:
{sections_list}

SOURCE CONTENT (Social Media Posts):
{source_content}

CRITICAL INSTRUCTIONS:
1. Write about the TOPIC indicated in the title, NOT about the Facebook page or source.
2. The article should be about the CONTENT of the posts, not about who posted them.
3. Write in a neutral, encyclopedic tone similar to Wikipedia.
4. Synthesize information from multiple posts into coherent paragraphs.
5. Do NOT mention that this content came from Facebook or social media.
6. Do NOT invent facts not present in the source content.
7. Do NOT use first-person perspective.
8. Do NOT include promotional language.
9. Organize content logically under the provided sections.
10. Include relevant details, dates, and names when available.
11. Write complete sentences with proper grammar.
12. The output language MUST match the source content language.
13. Preserve the original dialect if the content is in Arabic.

OUTPUT FORMAT:
Start with a brief introduction paragraph about the topic.
Then write each section with its header followed by content.
Use ## for section headers.
Do not include the title in the output.

"""

        if feedback:
            prompt += f"""
IMPORTANT REVISION FEEDBACK:
{feedback}

Please revise the article addressing the above feedback while maintaining encyclopedic quality.
"""

        return prompt

    def _get_language_instruction(self, language: str, dialect: str = None) -> str:
        if language == "ar":
            dialect_map = {
                "egyptian": "Egyptian Arabic (العامية المصرية)",
                "gulf": "Gulf Arabic (اللهجة الخليجية)",
                "levantine": "Levantine Arabic (اللهجة الشامية)",
                "maghrebi": "Maghrebi Arabic (اللهجة المغاربية)",
                "modern_standard_arabic": "Modern Standard Arabic (الفصحى)",
            }
            dialect_name = dialect_map.get(dialect, "Modern Standard Arabic")
            return f"""LANGUAGE REQUIREMENT: Write the entire article in Arabic.
DIALECT: Use {dialect_name} to match the source content.
Do NOT translate to English under any circumstances."""

        return """LANGUAGE REQUIREMENT: Write the entire article in English.
Use formal, encyclopedic English appropriate for reference material."""

    def _parse_generated_content(
        self,
        generated_text: str,
        article_plan: ArticlePlan,
    ) -> ArticleContent:
        lines = generated_text.strip().split("\n")

        sections: Dict[str, str] = {}
        current_section = None
        current_content = []
        body_parts = []
        intro_parts = []
        in_intro = True

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                elif in_intro:
                    intro_parts = current_content.copy()

                current_section = stripped[3:].strip()
                current_content = []
                in_intro = False

            elif stripped.startswith("# "):
                continue

            else:
                current_content.append(line)
                body_parts.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        intro = "\n".join(intro_parts).strip()
        body = "\n".join(body_parts).strip()

        return ArticleContent(
            title=article_plan.title,
            summary=intro if intro else article_plan.summary,
            body=body,
            sections=sections,
            language=article_plan.language,
            dialect=article_plan.dialect,
        )
