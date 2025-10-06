# @title Helper Functions

import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
from typing import Dict, List, Optional, Union

from google.genai.types import (
    DynamicRetrievalConfig,
    GenerateContentConfig,
    GoogleSearchRetrieval,
    Tool,
)
from pydantic import BaseModel, Field
from rich import print as rich_print
from termcolor import colored


class GeminiResponseSchema(BaseModel):
    class CitationSchema(BaseModel):
        number: int
        value: str
        source: str
        context: Optional[str] = ""

    enhanced_content: str = Field(description="Additional analysis with citations [n]")
    citations: List[CitationSchema]
    uncited_claims: List[str] = Field(default_factory=list)
    analysis_gaps: List[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class CitationData(BaseModel):
    number: int
    value: str
    data_path: str
    raw_value: Optional[str] = ""
    context: Optional[str] = ""


@dataclass
class Section:
    title: str
    content: str
    citations: Dict[int, CitationData]
    key_findings: List[str]
    enhanced_content: Optional[str] = None


@dataclass
class Report:
    city: str
    state: str
    timestamp: datetime
    sections: Dict[str, Section]
    citations_text: str
    full_text: str
    combined_report: str


class SearchCitation(BaseModel):
    number: int
    value: str
    source: str
    context: str = Field(default="")


class SearchEnhancement(BaseModel):
    enhanced_content: str = Field(description="Additional analysis with citations [n]")
    citations: List[SearchCitation]
    uncited_claims: List[str] = Field(default_factory=list)
    analysis_gaps: List[str] = Field(default_factory=list)


class ReportAgent:
    def __init__(
        self, client, model_name: str, enable_search: bool = False, debug: bool = False
    ):
        self.client = client
        self.model_name = model_name
        self.enable_search = enable_search
        self.citation_counter = 0
        self.debug = debug
        # print("self.debug", self.debug)
        if not self.debug:
            rich_print(
                "[bold yellow]ℹ️ Warning: Assembling the pieces of the puzzle!  It's like a jigsaw, but with more numbers and less chance of losing pieces under the couch.  Want a sneak peek at the final picture? debug=True is your magnifying glass! (And if you want to see the output of each agent stage, set stage_output=True!) 🧩🔍 [/bold yellow]"
            )

    def log_info(self, msg: str):
        print(colored(f"INFO: {msg}", "green", attrs=["bold"]))

    def log_debug(self, msg: str):
        print(colored(f"DEBUG: {msg}", "yellow", attrs=["bold"]))

    def log_process(self, msg: str):
        print(colored(f"🔄 {msg}", "cyan", attrs=["bold"]))

    def log_error(self, msg: str):
        print(colored(f"ERROR: {msg}", "red", attrs=["bold"]))

    async def _generate_section(
        self, section_name: str, city_data, agent_1_result
    ) -> Optional[Section]:

        if self.debug:
            self.log_info(f"Generating {section_name}...")

        data_map = self._prepare_data_map(city_data)
        formatted_data = json.dumps(data_map, indent=2)

        prompt = f"""Generate {section_name} for EV infrastructure analysis in {city_data.summary.city}, {city_data.summary.state}. Return JSON without markdown code fences:
      {{
          "content": "Analysis text with citations [n]",
          "citations": [
              {{
                  "number": int,
                  "value": "cited value",
                  "data_path": "path.to.data",
                  "raw_value": "original value",
                  "context": "how value is used"
              }}
          ],
          "key_findings": ["finding 1", "finding 2", "finding 3"],
          "subsections": ["section 1", "section 2"]
      }}
      Requirements:
      1. Use data points with citation numbers [n]
      2. Min 5 data points with citations
      3. Min 3 paragraphs
      4. Use markdown headings
      5. Include source data paths

      Guidelines:
      1. Use specific data points with citation numbers [n]
      2. Focus on EV charging infrastructure implications
      3. Provide actionable insights supported by data
      4. Structure with clear subsections
      5. Stay grounded in provided data
      6. Format in professional financial report style
      7. Use markdown formatting
      8. Focus on quantitative analysis

      Available data:
      {formatted_data}
      """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            # Clean response text of markdown code fences
            cleaned_json = response.text.replace("```json\n", "").replace("\n```", "")
            data = json.loads(cleaned_json)

            citations = {}
            for c in data.get("citations", []):
                try:
                    if c.get("value") and c.get(
                        "data_path"
                    ):  # Only process valid citations
                        citations[c["number"]] = CitationData(
                            number=c["number"],
                            value=str(c["value"]),  # Ensure string
                            data_path=str(c["data_path"]),  # Ensure string
                            raw_value=str(c.get("raw_value", c["value"])),
                            context=str(c.get("context", "")),
                        )
                except Exception as citation_error:
                    self.log_error(f"Citation processing error: {citation_error}")
                    continue

            return Section(
                title=section_name,
                content=data["content"],
                citations=citations,
                key_findings=data["key_findings"],
            )

        except Exception as e:
            self.log_error(f"{section_name} generation failed: {str(e)}")
            return None

    def _prepare_data_map(self, city_data) -> Dict:
        """Prepare complete data mapping with paths."""
        summary = city_data.summary
        ev_data = city_data.ev_data

        return {
            "infrastructure": {
                "area_metrics": {
                    "total_area": {
                        "value": f"{summary.area_metrics.total_area_sqkm:.2f}",
                        "path": "summary.area_metrics.total_area_sqkm",
                        "unit": "sq km",
                    },
                    "water_area": {
                        "value": f"{summary.area_metrics.water_area_sqkm:.2f}",
                        "path": "summary.area_metrics.water_area_sqkm",
                        "unit": "sq km",
                    },
                    "green_area": {
                        "value": f"{summary.area_metrics.green_area_sqkm:.2f}",
                        "path": "summary.area_metrics.green_area_sqkm",
                        "unit": "sq km",
                    },
                    "built_area": {
                        "value": f"{summary.area_metrics.built_area_sqkm:.2f}",
                        "path": "summary.area_metrics.built_area_sqkm",
                        "unit": "sq km",
                    },
                },
                "roads": {
                    "motorways": {
                        "value": str(summary.roads.motorways),
                        "path": "summary.roads.motorways",
                        "unit": "roads",
                    },
                    "trunks": {
                        "value": str(summary.roads.trunks),
                        "path": "summary.roads.trunks",
                        "unit": "roads",
                    },
                    "primary": {
                        "value": str(summary.roads.primary_roads),
                        "path": "summary.roads.primary_roads",
                        "unit": "roads",
                    },
                    "secondary": {
                        "value": str(summary.roads.secondary_roads),
                        "path": "summary.roads.secondary_roads",
                        "unit": "roads",
                    },
                    "tertiary": {
                        "value": str(summary.roads.tertiary_roads),
                        "path": "summary.roads.tertiary_roads",
                        "unit": "roads",
                    },
                    "residential": {
                        "value": str(summary.roads.residential_roads),
                        "path": "summary.roads.residential_roads",
                        "unit": "roads",
                    },
                    "service": {
                        "value": str(summary.roads.service_roads),
                        "path": "summary.roads.service_roads",
                        "unit": "roads",
                    },
                },
                "transport": {
                    "bus_stops": {
                        "value": str(summary.transport.bus_stops),
                        "path": "summary.transport.bus_stops",
                        "unit": "stops",
                    },
                    "train_stations": {
                        "value": str(summary.transport.train_stations),
                        "path": "summary.transport.train_stations",
                        "unit": "stations",
                    },
                    "bus_stations": {
                        "value": str(summary.transport.bus_stations),
                        "path": "summary.transport.bus_stations",
                        "unit": "stations",
                    },
                    "bike_rental": {
                        "value": str(summary.transport.bike_rental),
                        "path": "summary.transport.bike_rental",
                        "unit": "locations",
                    },
                },
                "buildings": {
                    "residential": {
                        "value": str(summary.buildings.residential),
                        "path": "summary.buildings.residential",
                        "unit": "buildings",
                    },
                    "apartments": {
                        "value": str(summary.buildings.apartments),
                        "path": "summary.buildings.apartments",
                        "unit": "buildings",
                    },
                    "commercial": {
                        "value": str(summary.buildings.commercial),
                        "path": "summary.buildings.commercial",
                        "unit": "buildings",
                    },
                    "retail": {
                        "value": str(summary.buildings.retail),
                        "path": "summary.buildings.retail",
                        "unit": "buildings",
                    },
                    "industrial": {
                        "value": str(summary.buildings.industrial),
                        "path": "summary.buildings.industrial",
                        "unit": "buildings",
                    },
                    "office": {
                        "value": str(summary.buildings.office),
                        "path": "summary.buildings.office",
                        "unit": "buildings",
                    },
                    "government": {
                        "value": str(summary.buildings.government),
                        "path": "summary.buildings.government",
                        "unit": "buildings",
                    },
                },
                "retail": {
                    "malls": {
                        "value": str(summary.retail.malls),
                        "path": "summary.retail.malls",
                        "unit": "buildings",
                    },
                    "supermarkets": {
                        "value": str(summary.retail.supermarkets),
                        "path": "summary.retail.supermarkets",
                        "unit": "stores",
                    },
                    "shopping_centres": {
                        "value": str(summary.retail.shopping_centres),
                        "path": "summary.retail.shopping_centres",
                        "unit": "locations",
                    },
                },
                "parking": {
                    "structures": {
                        "value": str(summary.parking.parking_structures),
                        "path": "summary.parking.parking_structures",
                        "unit": "structures",
                    },
                    "surface": {
                        "value": str(summary.parking.surface_parking),
                        "path": "summary.parking.surface_parking",
                        "unit": "lots",
                    },
                    "bike_parking": {
                        "value": str(summary.parking.bike_parking),
                        "path": "summary.parking.bike_parking",
                        "unit": "locations",
                    },
                    "ev_charging": {
                        "value": str(summary.parking.ev_charging),
                        "path": "summary.parking.ev_charging",
                        "unit": "stations",
                    },
                },
            },
            "ev_infrastructure": {
                "overview": {
                    "total_stations": {
                        "value": str(ev_data.metadata["total_stations"]),
                        "path": "ev_data.metadata.total_stations",
                        "unit": "stations",
                    },
                    "city_area": {
                        "value": f"{ev_data.metadata['city_area_square_miles']:.2f}",
                        "path": "ev_data.metadata.city_area_square_miles",
                        "unit": "sq miles",
                    },
                },
                "charging_capabilities": {
                    "dc_fast": {
                        "value": str(
                            ev_data.charging_capabilities.by_type["dc_fast"].count
                        ),
                        "path": "ev_data.charging_capabilities.by_type.dc_fast",
                        "unit": "chargers",
                        "ports": str(
                            ev_data.charging_capabilities.by_type["dc_fast"].total_ports
                        ),
                    },
                    "level2": {
                        "value": str(
                            ev_data.charging_capabilities.by_type["level2"].count
                        ),
                        "path": "ev_data.charging_capabilities.by_type.level2",
                        "unit": "chargers",
                        "ports": str(
                            ev_data.charging_capabilities.by_type["level2"].total_ports
                        ),
                    },
                    "level1": {
                        "value": str(
                            ev_data.charging_capabilities.by_type["level1"].count
                        ),
                        "path": "ev_data.charging_capabilities.by_type.level1",
                        "unit": "chargers",
                        "ports": str(
                            ev_data.charging_capabilities.by_type["level1"].total_ports
                        ),
                    },
                },
                "accessibility": {
                    "24_7_access": {
                        "value": f"{ev_data.accessibility.access_type['24_7_access']['percentage']:.1f}",
                        "path": "ev_data.accessibility.access_type.24_7_access.percentage",
                        "unit": "%",
                    },
                    "public_access": {
                        "value": f"{ev_data.accessibility.access_type['public']['percentage']:.1f}",
                        "path": "ev_data.accessibility.access_type.public.percentage",
                        "unit": "%",
                    },
                    "payment_methods": {
                        "credit_card": {
                            "value": f"{ev_data.accessibility.payment_methods['credit_card']['percentage']:.1f}",
                            "path": "ev_data.accessibility.payment_methods.credit_card.percentage",
                            "unit": "%",
                        },
                        "mobile_pay": {
                            "value": f"{ev_data.accessibility.payment_methods['mobile_pay']['percentage']:.1f}",
                            "path": "ev_data.accessibility.payment_methods.mobile_pay.percentage",
                            "unit": "%",
                        },
                    },
                },
                "network_analysis": {
                    "networks": [
                        {
                            "name": net.name,
                            "count": str(net.station_count),
                            "percentage": f"{net.percentage:.1f}",
                        }
                        for net in ev_data.network_analysis.networks
                    ],
                    "pricing": {
                        "free": {
                            "value": f"{ev_data.network_analysis.pricing_types['free']['percentage']:.1f}",
                            "path": "ev_data.network_analysis.pricing_types.free.percentage",
                            "unit": "%",
                        },
                        "paid": {
                            "value": f"{ev_data.network_analysis.pricing_types['paid']['percentage']:.1f}",
                            "path": "ev_data.network_analysis.pricing_types.paid.percentage",
                            "unit": "%",
                        },
                    },
                },
                "station_age": {
                    "more_than_3_years": {
                        "value": f"{ev_data.station_age.age_distribution['more_than_3_years']['percentage']:.1f}",
                        "path": "ev_data.station_age.age_distribution.more_than_3_years.percentage",
                        "unit": "%",
                    },
                    "last_verified": {
                        "last_30_days": {
                            "value": f"{ev_data.station_age.last_verified['last_30_days']['percentage']:.1f}",
                            "path": "ev_data.station_age.last_verified.last_30_days.percentage",
                            "unit": "%",
                        },
                        "last_90_days": {
                            "value": f"{ev_data.station_age.last_verified['last_90_days']['percentage']:.1f}",
                            "path": "ev_data.station_age.last_verified.last_90_days.percentage",
                            "unit": "%",
                        },
                    },
                },
            },
        }

    async def analyze(
        self, agent_1_result: dict, data_output
    ) -> Union[Report, List[Report]]:

        if self.debug:
            self.log_process("Starting analysis...")

        reports = []
        for city, city_data in zip(
            agent_1_result["entities"]["cities"], data_output.cities_data
        ):
            if self.debug:
                self.log_info(f"Processing {city}")
            sections = await self._generate_sections(city_data, agent_1_result)

            if self.enable_search:
                sections = await self.enhance_sections(sections, city_data)

            report = self._assemble_report(city_data, sections)
            reports.append(report)

        return reports[0] if len(reports) == 1 else reports

    async def _generate_sections(self, city_data, agent_1_result) -> Dict[str, Section]:
        if self.debug:
            self.log_process("Generating sections...")

        section_names = [
            "Executive Summary",
            "Infrastructure Overview",
            "Current EV Assessment",
            "Demand Analysis",
            "Supply Analysis",
            "Gap Analysis",
            "Location Recommendations",
            "Implementation Strategy",
        ]

        tasks = [
            self._generate_section(name, city_data, agent_1_result)
            for name in section_names
        ]

        sections = await asyncio.gather(*tasks)
        return {s.title: s for s in sections if s}

    def _assemble_report(self, city_data, sections: Dict[str, Section]) -> Report:
        if self.debug:
            self.log_process("Assembling report...")

        full_text = []
        citations_text = []

        full_text.extend(
            [
                f"# EV Infrastructure Analysis Report: {city_data.summary.city}, {city_data.summary.state}\n",
                f"Generated on {datetime.now().strftime('%B %d, %Y')}\n",
            ]
        )

        for section in sections.values():
            full_text.extend([f"\n## {section.title}\n", section.content])

            if section.enhanced_content:
                full_text.extend(
                    ["\n### Additional Research\n", section.enhanced_content]
                )

            if section.citations:
                citations_text.extend(
                    [
                        f"\n### {section.title} Citations\n",
                        *[
                            f"[{num}] {cit.value} (Data: {cit.data_path})"
                            for num, cit in sorted(section.citations.items())
                        ],
                        "",
                    ]
                )

        full_text = "\n".join(full_text)
        citations = "\n".join(citations_text)

        return Report(
            city=city_data.summary.city,
            state=city_data.summary.state,
            timestamp=datetime.now(),
            sections=sections,
            citations_text=citations,
            full_text=full_text,
            combined_report=f"{full_text}\n\n## Citations\n{citations}",
        )

    async def _enhance_section_with_search(
        self, section: Section, city_data
    ) -> Section:
        """
        Enhances a section with search data and proper citation handling.
        """
        if not self.enable_search:
            return section

        if self.debug:
            self.log_process(f"Enhancing section {section.title} with search data...")

        try:
            # Define schema for Gemini response
            response_schema = {
                "type": "object",
                "properties": {
                    "enhanced_content": {
                        "type": "string",
                        "description": "Additional analysis with citations [n]",
                    },
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "number": {"type": "integer"},
                                "value": {"type": "string"},
                                "source": {"type": "string"},
                                "context": {"type": "string"},
                            },
                            "required": ["number", "value", "source"],
                        },
                    },
                    "uncited_claims": {"type": "array", "items": {"type": "string"}},
                    "analysis_gaps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["enhanced_content", "citations"],
            }

            prompt = f"""You are enhancing an EV infrastructure analysis section with additional data from search.

          Section to enhance: {section.title}
          City: {city_data.summary.city}
          
          Current analysis:
          {section.content}
          
          Requirements:
          1. Add supporting data with citations for existing analysis
          2. Cross-check uncited claims and add citations
          3. Add new relevant insights with citations
          4. Point out any analysis gaps
          5. Support with recent internet data

          Return ONLY valid JSON matching the specified schema.
          Make sure all analysis is properly cited.
          """

            # Get response with grounding
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    tools=[
                        Tool(
                            google_search_retrieval=GoogleSearchRetrieval(
                                dynamic_retrieval_config=DynamicRetrievalConfig(
                                    dynamic_threshold=0.7, mode="MODE_DYNAMIC"
                                )
                            )
                        )
                    ],
                ),
            )

            # Clean and validate response text
            response_text = response.text.strip()
            if response_text.endswith('",'):  # Fix unterminated string
                response_text = response_text[:-1] + '"}'
            if not response_text.endswith("}"):
                response_text += "}"

            # Get grounding metadata safely
            grounding_metadata = None
            source_urls = {}  # Map to store source URLs

            if response.candidates and response.candidates[0].grounding_metadata:
                grounding_metadata = response.candidates[0].grounding_metadata

                # Extract URLs from grounding chunks if available
                if hasattr(grounding_metadata, "grounding_chunks"):
                    chunks = grounding_metadata.grounding_chunks
                    if chunks and isinstance(chunks, list):
                        for i, chunk in enumerate(chunks):
                            if hasattr(chunk, "web") and chunk.web and chunk.web.uri:
                                source_urls[i] = chunk.web.uri

            # Parse response
            try:
                data = json.loads(response_text)
                validated_data = GeminiResponseSchema(**data)
            except (json.JSONDecodeError, ValidationError) as e:
                self.log_error(f"Data validation error: {str(e)}")
                raise

            # Create enhanced content
            enhanced_text = [
                "\n### Enhanced with Search Data\n",
                validated_data.enhanced_content,
            ]

            if validated_data.analysis_gaps:
                enhanced_text.extend(
                    [
                        "\n#### Analysis Gaps Identified\n",
                        *[f"- {gap}" for gap in validated_data.analysis_gaps],
                    ]
                )

            if validated_data.uncited_claims:
                enhanced_text.extend(
                    [
                        "\n#### Claims Requiring Citations\n",
                        *[f"- {claim}" for claim in validated_data.uncited_claims],
                    ]
                )

            # Add new citations with proper URL handling
            start_num = max(section.citations.keys()) + 1 if section.citations else 1

            for i, citation in enumerate(validated_data.citations, start=start_num):
                # Get URL from source_urls map or use source as fallback
                source_url = source_urls.get(i - start_num, citation.source)
                if not source_url or source_url.lower() in ["no url", "unknown"]:
                    # Try to extract URL from the source field if it looks like a URL
                    if citation.source and (
                        "http" in citation.source.lower()
                        or "www." in citation.source.lower()
                    ):
                        source_url = citation.source
                    else:
                        source_url = f"Source: {citation.source}"

                # Create citation text with enhanced information
                citation_text = f"{citation.value}"
                if citation.context:
                    citation_text += f" | Context: {citation.context}"
                citation_text += f" | URL: {source_url}"

                section.citations[i] = CitationData(
                    number=i,
                    value=citation_text,
                    data_path=source_url,
                    raw_value=citation.value,
                    context=citation.context,
                )

            section.enhanced_content = "\n".join(enhanced_text)
            return section

        except Exception as e:
            self.log_error(f"Enhancement failed for {section.title}: {str(e)}")
            section.enhanced_content = "\n### Enhanced with Search Data\nEnhancement failed due to technical issues."
            # Add a placeholder citation to maintain structure
            if not section.citations:
                section.citations[1] = CitationData(
                    number=1,
                    value="Enhancement failed",
                    data_path="Error occurred during enhancement",
                    raw_value="",
                    context="",
                )
            return section

    async def enhance_sections(
        self, sections: Dict[str, Section], city_data
    ) -> Dict[str, Section]:
        if self.debug:
            self.log_process("Enhancing sections with external data...")
        enhanced = {}

        for name, section in sections.items():
            enhanced[name] = await self._enhance_section_with_search(section, city_data)
            self.log_debug(
                f"Enhanced {name} with {len(section.citations)} new citations"
            )

        return enhanced

    async def enhance_all_sections(
        self, sections: Dict[str, Section], city_data
    ) -> Dict[str, Section]:
        enhanced = {}
        for name, section in sections.items():
            enhanced[name] = await self._safe_generate(
                self._enhance_section_with_search, section, city_data
            )
        return enhanced
