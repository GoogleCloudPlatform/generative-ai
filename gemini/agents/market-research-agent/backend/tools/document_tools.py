import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DocumentTools:
    """Tools for document generation and formatting."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the document tools.

        Args:
            output_dir: Optional directory for saving documents.
        """
        self.output_dir = Path(output_dir) if output_dir else Path("outputs/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_use_cases_markdown(
        self,
        use_cases: List[Dict[str, Any]],
        company_info: Dict[str, Any],
        industry_info: Dict[str, Any],
        resources: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Format use cases as a Markdown document.

        Args:
            use_cases: List of use case dictionaries.
            company_info: Company information.
            industry_info: Industry information.
            resources: Dictionary mapping use case titles to resources.

        Returns:
            Markdown formatted document.
        """
        # Generate document title
        title = f"AI and GenAI Use Case Proposal for {company_info.get('name', 'Your Company')}"

        # Generate document header
        header = f"""# {title}
        
        ## Executive Summary

        This proposal outlines strategic AI and Generative AI (GenAI) use cases for {company_info.get("name", "your company")} in the {company_info.get("industry", "")} industry. The proposed use cases are designed to enhance operational efficiency, improve customer experiences, and create competitive advantages.

        **Generated on:** {datetime.now().strftime("%B %d, %Y")}

        ## Company Overview

        **Company:** {company_info.get("name", "")}  
        **Industry:** {company_info.get("industry", "")}  
        **Description:** {company_info.get("description", "")}

        ### Products and Services
        {self._format_bullet_list(company_info.get("products", []))}

        ### Industry Insights
        {industry_info.get("description", "")}

        #### Key Industry Trends
        {self._format_bullet_list(industry_info.get("trends", []))}

        #### Industry Challenges
        {self._format_bullet_list(industry_info.get("challenges", []))}

        ## AI and GenAI Use Cases

        """

        # Generate use case sections
        use_case_sections = []
        for i, use_case in enumerate(use_cases):
            title = use_case.get("title", f"Use Case {i + 1}")
            description = use_case.get("description", "")
            business_value = use_case.get("business_value", "")
            complexity = use_case.get("implementation_complexity", "Medium")
            ai_technologies = use_case.get("ai_technologies", [])
            priority_score = use_case.get("priority_score", 0)
            prioritization_rationale = use_case.get("prioritization_rationale", "")

            # Format cross-functional benefits
            cross_functional_benefits = use_case.get("cross_functional_benefits", [])
            benefits_text = ""
            if cross_functional_benefits:
                benefits_text = "### Cross-Functional Benefits\n\n"
                for benefit in cross_functional_benefits:
                    department = benefit.get("department", "")
                    benefit_desc = benefit.get("benefit", "")
                    benefits_text += f"**{department}:** {benefit_desc}\n\n"

            # Format resources
            resources_text = ""
            use_case_resources = resources.get(title, [])
            if use_case_resources:
                resources_text = "### Implementation Resources\n\n"
                for resource in use_case_resources:
                    resource_title = resource.get("title", "")
                    resource_url = resource.get("url", "")
                    resource_source = resource.get("source", "").capitalize()
                    resources_text += (
                        f"- [{resource_title}]({resource_url}) ({resource_source})\n"
                    )

            # Format use case section
            section = f"""### {i + 1}. {title}
            **Priority Score:** {priority_score}/10  
            **Implementation Complexity:** {complexity}  
            **AI Technologies:** {", ".join(ai_technologies)}

            #### Description
            {description}

            #### Business Value
            {business_value}

            #### Prioritization Rationale
            {prioritization_rationale}

            {benefits_text}
            {resources_text}
            """
            use_case_sections.append(section)

        # Combine all sections
        document = header + "\n\n".join(use_case_sections)

        # Add conclusion
        conclusion = f"""
        ## Conclusion

        The proposed AI and GenAI use cases present significant opportunities for {company_info.get("name", "your company")} to enhance operations, improve customer experiences, and gain competitive advantages in the {company_info.get("industry", "")} industry. We recommend starting with the highest priority use cases and developing a phased implementation roadmap.

        For each use case, we've provided relevant datasets and implementation resources to accelerate development and reduce implementation risks.
        """

        document += conclusion

        return document

    def save_use_cases_markdown(self, markdown: str, company_name: str) -> str:
        """Save use cases as a Markdown file.

        Args:
            markdown: Markdown formatted document.
            company_name: Name of the company.

        Returns:
            Path to the saved file.
        """
        # Clean company name for filename
        clean_name = "".join(c if c.isalnum() else "_" for c in company_name.lower())

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{clean_name}_use_cases_{timestamp}.md"
        file_path = self.output_dir / filename

        # Save the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        logger.info(f"Saved use cases to {file_path}")
        return str(file_path)

    def save_use_cases_json(
        self,
        use_cases: List[Dict[str, Any]],
        company_info: Dict[str, Any],
        industry_info: Dict[str, Any],
        resources: Dict[str, List[Dict[str, Any]]],
        company_name: str,
    ) -> str:
        """Save use cases as a JSON file.

        Args:
            use_cases: List of use case dictionaries.
            company_info: Company information.
            industry_info: Industry information.
            resources: Dictionary mapping use case titles to resources.
            company_name: Name of the company.

        Returns:
            Path to the saved file.
        """
        # Clean company name for filename
        clean_name = "".join(c if c.isalnum() else "_" for c in company_name.lower())

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{clean_name}_use_cases_{timestamp}.json"
        file_path = self.output_dir / filename

        # Prepare data
        data = {
            "company_info": company_info,
            "industry_info": industry_info,
            "use_cases": use_cases,
            "resources": resources,
            "generated_at": datetime.now().isoformat(),
        }

        # Save the file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved use cases to {file_path}")
        return str(file_path)

    def _format_bullet_list(self, items: List[str]) -> str:
        """Format a list of items as a Markdown bullet list.

        Args:
            items: List of items.

        Returns:
            Markdown formatted bullet list.
        """
        if not items:
            return "No information available."

        return "\n".join([f"- {item}" for item in items])
