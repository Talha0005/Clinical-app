"""NICE CKS topics scraper."""

import json
import asyncio
import random
from pathlib import Path
from typing import Dict

from playwright.async_api import async_playwright
import re


def clean_extracted_content(raw_text: str) -> str:
    """Clean extracted text content by removing HTML artifacts, JSON-LD, navigation, etc."""
    if not raw_text:
        return ""

    # Remove JSON-LD structured data
    cleaned = re.sub(r'\{["\']@context["\'].*?\}', "", raw_text, flags=re.DOTALL)

    # Remove common HTML artifacts and navigation elements
    navigation_patterns = [
        r"NICE\s*CKS\s*Health topics A to Z",
        r"Print this page",
        r"Back to top",
        r"Skip to main content",
        r"Skip to navigation",
        r"Search\s*for\s*topics",
        r"Browse topics A to Z",
        r"Last revised in [A-Za-z]+ \d{4}",
        r"How up-to-date is this topic\?",
        r"Have I got the right topic\?",
        r"Goals and outcome measures",
        r"Supporting evidence",
        r"How this topic was developed",
        r"References",
        r"The content on the NICE Clinical Knowledge Summaries",
        r"By using CKS, you agree to the licence",
        r"CKS End User Licence Agreement",
        r"Clarity Informatics Limited",
        r"trading as Agilio Software",
        r"@context",
        r"@type",
        r"BreadcrumbList",
        r"ListItem",
        r"itemListElement",
        r"position",
        r"https://www\.nice\.org\.uk",
        r"https://schema\.org",
    ]

    for pattern in navigation_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Split into lines and filter
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]

    # More aggressive filtering of non-medical content
    filtered_lines = []
    skip_phrases = [
        "copyright",
        "licence",
        "license",
        "cookies",
        "navigation",
        "menu",
        "skip to",
        "back to top",
        "accessibility",
        "print this page",
        "feedback",
        "find out more",
        "browse topics",
        "search for topics",
        "nice cks",
        "health topics a to z",
        "summary",
        "management",
        "background information",
        "scenario",
        "supporting evidence",
        "references",
        "how this topic",
        "goals and outcome",
        "have i got the right",
        "up-to-date",
        "clarity informatics",
        "agilio software",
        "end user licence",
        '"@',
        "itemlistelement",
        "breadcrumblist",
        "listitem",
    ]

    for line in lines:
        line_lower = line.lower()
        # Skip if line is too short or contains navigation elements
        if (
            len(line) < 15
            or any(skip in line_lower for skip in skip_phrases)
            or line.startswith("{")
            or line.startswith("[")
            or '"@' in line
            or "http://" in line
            or "https://" in line
        ):
            continue

        # Keep lines that seem to contain medical content
        medical_indicators = [
            "aaa",
            "aneurysm",
            "screening",
            "diagnosis",
            "treatment",
            "patient",
            "medical",
            "condition",
            "symptom",
            "risk",
            "factor",
            "prevalence",
            "management",
            "therapy",
            "clinical",
            "health",
            "nhs",
            "care",
            "ultrasound",
            "scan",
            "vascular",
            "surgeon",
            "surveillance",
        ]

        # If line has medical content or is substantial, keep it
        if (
            any(indicator in line_lower for indicator in medical_indicators)
            or len(line) > 50
        ):
            filtered_lines.append(line)

    # Join and clean up spacing
    result = "\n".join(filtered_lines)

    # Final cleanup - remove multiple newlines and extra spaces
    result = re.sub(r"\n\s*\n\s*\n+", "\n\n", result)
    result = re.sub(r"  +", " ", result)

    return result.strip()


async def extract_section_content(page, section_name: str) -> str:
    """Extract content from a specific NICE CKS section page."""
    try:
        print(f"  🔍 Extracting content from {section_name} section...")

        # Wait for page to load
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        # Accept cookies if needed
        try:
            accept_btn = page.locator('button:has-text("Accept all cookies")')
            if await accept_btn.count() > 0:
                await accept_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass

        content = ""

        # Try to extract content using the ChapterBody selector
        chapter_body = page.locator(".ChapterBody-module--body--ad48a")
        chapter_count = await chapter_body.count()

        if chapter_count > 0:
            # If multiple chapter bodies, combine them all
            if chapter_count > 1:
                print(
                    f"    Found {chapter_count} ChapterBody sections, combining all..."
                )
                all_text = []
                for i in range(chapter_count):
                    section_text = await chapter_body.nth(i).text_content()
                    if section_text:
                        all_text.append(section_text.strip())
                chapter_text = "\n\n".join(all_text)
            else:
                chapter_text = await chapter_body.text_content()

            if chapter_text:
                content = clean_extracted_content(chapter_text)

        # If ChapterBody didn't work, try alternative selectors
        if not content:
            alternative_selectors = [
                "main section",  # Main section content
                ".content-area",  # Content area
                "article",  # Article content
                ".topic-content",  # Topic specific content
                "main",  # Main element
            ]

            for selector in alternative_selectors:
                elem = page.locator(selector)
                if await elem.count() > 0:
                    text = await elem.first.text_content()
                    if text and len(text.strip()) > 100:
                        content = clean_extracted_content(text)
                        if content:  # Only break if we got clean content
                            break

        # Extract subsection information for Background sections using direct element targeting
        if section_name.lower() == "background":
            print(f"    🔍 Extracting Background subsections...")
            subsection_content = {}

            # Target specific subsection patterns
            subsection_patterns = [
                "Definition",
                "Prevalence",
                "Risk factors",
                "Eligibility for routine AAA screening",
                "Programme coordination and management",
                "The AAA screening test",
                "Benefits and harms of AAA screening",
            ]

            # Try to find subsections using heading + content patterns
            for pattern in subsection_patterns:
                try:
                    # Look for headings with this text
                    heading_selectors = [
                        f'h2:has-text("{pattern}")',
                        f'h3:has-text("{pattern}")',
                        f'h4:has-text("{pattern}")',
                        f'[id*="{pattern.lower().replace(" ", "-")}"]',
                        f'*:has-text("{pattern}"):not(a):not(span)',
                    ]

                    for selector in heading_selectors:
                        heading = page.locator(selector)
                        if await heading.count() > 0:
                            # Try to get content after this heading
                            following_content_selectors = [
                                f"{selector} + div",
                                f"{selector} + p",
                                f"{selector} + ul",
                                f"{selector} ~ p",
                                f"{selector} ~ div",
                            ]

                            for content_selector in following_content_selectors:
                                content_elem = page.locator(content_selector)
                                if await content_elem.count() > 0:
                                    section_text = (
                                        await content_elem.first.text_content()
                                    )
                                    if section_text and len(section_text.strip()) > 20:
                                        subsection_content[pattern] = (
                                            section_text.strip()[:500]
                                        )
                                        print(
                                            f"      ✅ Found {pattern}: {len(section_text)} chars"
                                        )
                                        break
                            break

                except Exception as e:
                    print(f"      ❌ Error extracting {pattern}: {e}")
                    continue

            # If we found subsections, format them nicely
            if subsection_content:
                formatted_subsections = []
                for subsection_name, subsection_text in subsection_content.items():
                    formatted_subsections.append(
                        f"{subsection_name}:\n{subsection_text}"
                    )
                content = "\n\n".join(formatted_subsections)
                print(f"    ✅ Formatted {len(subsection_content)} subsections")
            else:
                print(f"    ⚠️  No specific subsections found, using general content")

        # Clean up the content
        if content:
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            # Remove duplicates while preserving order
            seen = set()
            clean_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    clean_lines.append(line)

            content = "\n".join(clean_lines)[:2000]  # Limit length per section

        return content

    except Exception as e:
        print(f"  ❌ Error extracting {section_name} content: {e}")
        return ""


async def extract_topic_details(page, url: str) -> Dict[str, str]:
    """Extract detailed information from a NICE CKS topic page."""
    try:
        print(f"🌐 Starting from main topic page: {url}")

        # Start from the main topic page (like manual browsing)
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        # Accept cookies first
        try:
            accept_btn = page.locator('button:has-text("Accept all cookies")')
            if await accept_btn.count() > 0:
                print("🍪 Accepting cookies...")
                await accept_btn.click()
                await page.wait_for_timeout(2000)
                print("✅ Cookies accepted")
        except Exception as e:
            print(f"⚠️  Cookie handling: {e}")

        # Wait for content to load
        await page.wait_for_timeout(3000)
        print("📄 Main page loaded successfully")

        # Check if we're on a license/terms page and try to navigate past it
        page_title = await page.title()
        page_text = await page.text_content("body")
        print(f"📋 Page title: {page_title}")

        if (
            "licence" in page_text.lower()
            or "license" in page_text.lower()
            or "copyright" in page_text.lower()
            or "terms" in page_text.lower()
        ):
            print(
                "⚠️  Detected license/terms page, looking for continue/accept buttons..."
            )

            # Look for buttons to continue past the license
            continue_buttons = [
                'button:has-text("Continue")',
                'button:has-text("Accept")',
                'button:has-text("Agree")',
                'button:has-text("I agree")',
                'button:has-text("Proceed")',
                'a:has-text("Continue")',
                'a:has-text("Enter")',
                'a:has-text("Access")',
                '[role="button"]:has-text("Continue")',
                '[role="button"]:has-text("Accept")',
            ]

            for selector in continue_buttons:
                try:
                    button = page.locator(selector).first
                    if await button.count() > 0:
                        print(f"  🔘 Found button: {selector}")
                        await button.click()
                        await page.wait_for_load_state("networkidle")
                        print("  ✅ Clicked continue button, waiting for content...")
                        await page.wait_for_timeout(2000)  # Wait a bit more
                        break
                except Exception as e:
                    print(f"  ❌ Failed to click {selector}: {e}")
                    continue

            # Check if we're still on license page
            new_page_text = await page.text_content("body")
            if (
                "licence" in new_page_text.lower() and len(new_page_text) < 1000
            ):  # Still seems like license page
                print("  ⚠️  Still on license page, trying direct navigation...")
                # Try to navigate to content directly
                if not url.endswith("/"):
                    content_url = url + "/"
                else:
                    content_url = url + "management/"  # Common NICE CKS pattern
                try:
                    await page.goto(content_url)
                    await page.wait_for_load_state("networkidle")
                    print(f"  🌐 Tried alternative URL: {content_url}")
                except:
                    pass

        details = {
            "summary": "",
            "symptoms": "",
            "causes": "",
            "treatments": "",
            "diagnosis": "",
            "management": "",
        }

        # Now look for content section links (like manual browsing)
        print("🔍 Looking for content section links...")

        # Find links to different content sections
        content_sections = ["Background", "Management", "Scenario", "Assessment"]
        section_links = {}

        for section in content_sections:
            links = page.locator(f'a:has-text("{section}")')
            count = await links.count()
            if count > 0:
                print(f"  📋 Found {count} {section} link(s)")
                for i in range(count):
                    link = links.nth(i)
                    href = await link.get_attribute("href")
                    text = await link.text_content()
                    if (
                        href and "background-information" not in href
                    ):  # Skip background info subitems
                        section_links[section] = {
                            "href": href,
                            "text": text,
                            "element": link,
                        }
                        print(f"    - {text}: {href}")
                        break

        # Extract main summary first, then navigate to other sections
        print("📄 Starting with main summary page content")
        content_extracted = True

        # Now extract content from the CKS page structure
        print("🔍 Extracting medical content from CKS page...")

        # Target the complete summary section content
        summary_content = ""

        # First, get the entire ChapterBody div content
        print("🔍 Extracting complete summary from ChapterBody section...")
        chapter_body = page.locator(".ChapterBody-module--body--ad48a")
        chapter_count = await chapter_body.count()
        print(f"  Found {chapter_count} ChapterBody sections")

        if chapter_count > 0:
            # Get all text content from the chapter body
            chapter_text = await chapter_body.text_content()
            if chapter_text:
                print(f"  Total chapter text length: {len(chapter_text)} characters")
                print(f"  Chapter text preview: {chapter_text[:200]}...")

                # Clean the content using the improved cleaning function
                summary_content = clean_extracted_content(chapter_text)
                print(f"  Cleaned summary length: {len(summary_content)} characters")

        # If ChapterBody didn't work, try alternative selectors
        if not summary_content:
            print("🔄 Trying alternative summary selectors...")
            alternative_selectors = [
                'section[aria-labelledby="summary"]',  # Complete summary section
                "h2#summary + div",  # Content after summary heading
                "main section:first-child",  # First main section
                '[id*="summary"]',  # Any element with summary in ID
            ]

            for i, selector in enumerate(alternative_selectors):
                print(f"  📝 Trying alternative selector {i+1}: {selector}")
                alt_elem = page.locator(selector)
                alt_count = await alt_elem.count()
                print(f"    Found {alt_count} elements")

                if alt_count > 0:
                    alt_text = await alt_elem.first.text_content()
                    if alt_text and len(alt_text.strip()) > 100:
                        summary_content = clean_extracted_content(alt_text)
                        if summary_content:
                            print(
                                f"  ✅ Found clean content with alternative selector: {selector}"
                            )
                            break

        # Process the extracted summary content
        if summary_content:
            details["summary"] = summary_content[:3000]  # Allow longer content
            print(f"  ✅ Clean summary extracted: {len(details['summary'])} characters")

            # Extract specific sections from the summary
            summary_lower = details["summary"].lower()
            summary_lines = details["summary"].split("\n")

            # Look for risk factors
            for i, line in enumerate(summary_lines):
                if "risk factors" in line.lower():
                    # Get this line and several following lines
                    risk_section = "\n".join(summary_lines[i : i + 10])
                    details["causes"] = risk_section[:800]
                    break

            # Look for screening/diagnosis info
            for i, line in enumerate(summary_lines):
                if any(
                    word in line.lower()
                    for word in ["screening", "diagnosis", "test", "ultrasound"]
                ):
                    diag_section = "\n".join(summary_lines[i : i + 5])
                    if not details["diagnosis"] or len(diag_section) > len(
                        details["diagnosis"]
                    ):
                        details["diagnosis"] = diag_section[:800]

            # Look for treatment/management info
            for i, line in enumerate(summary_lines):
                if any(
                    word in line.lower()
                    for word in ["treatment", "management", "primary care", "role"]
                ):
                    treatment_section = "\n".join(summary_lines[i : i + 8])
                    if not details["treatments"] or len(treatment_section) > len(
                        details["treatments"]
                    ):
                        details["treatments"] = treatment_section[:800]

        else:
            print("  ❌ No summary content found")

        # Now navigate to and extract content from additional sections
        additional_sections = {}

        print("🔄 Navigating to additional sections...")

        # Define sections we want to extract
        target_sections = [
            {"name": "Management", "keywords": ["management"], "key": "management"},
            {
                "name": "Scenario",
                "keywords": ["scenario", "aaa screening"],
                "key": "scenario",
            },
            {"name": "Background", "keywords": ["background"], "key": "background"},
        ]

        # Look for section links on the current page
        for section_info in target_sections:
            section_name = section_info["name"]
            section_key = section_info["key"]

            print(f"🔍 Looking for {section_name} section...")

            # Try different selectors to find the section link
            section_selectors = [
                f'a:has-text("{section_name}")',
                f'a[href*="{section_name.lower()}"]',
                f'nav a:has-text("{section_name}")',
                f'.navigation a:has-text("{section_name}")',
                f'ul li a:has-text("{section_name}")',
            ]

            section_found = False
            for selector in section_selectors:
                try:
                    section_links = page.locator(selector)
                    count = await section_links.count()

                    if count > 0:
                        for i in range(count):
                            link = section_links.nth(i)
                            text = await link.text_content()
                            href = await link.get_attribute("href")

                            # Check if this matches what we're looking for
                            if text and any(
                                keyword in text.lower()
                                for keyword in section_info["keywords"]
                            ):
                                print(
                                    f"  📝 Found {section_name} link: {text} -> {href}"
                                )

                                try:
                                    # Navigate to the section
                                    if href.startswith("/"):
                                        full_href = f"https://cks.nice.org.uk{href}"
                                    else:
                                        full_href = href

                                    await page.goto(full_href)
                                    await page.wait_for_load_state("networkidle")
                                    await page.wait_for_timeout(2000)

                                    print(f"  🌐 Navigated to {section_name} section")

                                    # Extract content from this section
                                    section_content = await extract_section_content(
                                        page, section_name
                                    )
                                    if section_content:
                                        additional_sections[section_key] = (
                                            section_content
                                        )
                                        print(
                                            f"  ✅ Extracted {len(section_content)} characters from {section_name}"
                                        )
                                    else:
                                        print(
                                            f"  ❌ No content extracted from {section_name}"
                                        )

                                    # Go back to main page for next section
                                    await page.goto(url)
                                    await page.wait_for_load_state("networkidle")
                                    await page.wait_for_timeout(1000)

                                    section_found = True
                                    break

                                except Exception as e:
                                    print(
                                        f"  ❌ Error navigating to {section_name}: {e}"
                                    )
                                    # Go back to main page
                                    try:
                                        await page.goto(url)
                                        await page.wait_for_load_state("networkidle")
                                    except:
                                        pass

                        if section_found:
                            break

                except Exception as e:
                    print(f"  ⚠️  Error with selector {selector}: {e}")
                    continue

            if not section_found:
                print(f"  ❌ Could not find {section_name} section")

        # Add the additional sections to details
        details.update(additional_sections)

        if not details["summary"]:
            print("  ❌ No summary found")

        # Extract symptoms with better selectors
        print("🔍 Looking for symptoms content...")
        symptoms_selectors = [
            'h2:has-text("Symptoms") + p, h2:has-text("Symptoms") + div p',
            'h3:has-text("Symptoms") + p, h3:has-text("Symptoms") + div p',
            'h2:has-text("Signs and symptoms") + p, h2:has-text("Signs and symptoms") + div p',
            'h2:has-text("Presentation") + p, h2:has-text("Presentation") + div p',
            'section:has-text("Symptoms") p',
            'section:has-text("Signs and symptoms") p',
            'section:has-text("Presentation") p',
            '[data-section="symptoms"] p',
            'div:has(h2:text("Symptoms")) p, div:has(h3:text("Symptoms")) p',
        ]

        for i, selector in enumerate(symptoms_selectors):
            print(
                f"  📝 Trying symptoms selector {i+1}/{len(symptoms_selectors)}: {selector}"
            )
            symptoms_elem = page.locator(selector).first
            count = await symptoms_elem.count()
            print(f"    Found {count} elements")
            if count > 0:
                symptoms_text = await symptoms_elem.text_content()
                print(
                    f"    Text preview: {symptoms_text[:100] if symptoms_text else 'None'}..."
                )
                if symptoms_text and len(symptoms_text.strip()) > 20:
                    details["symptoms"] = symptoms_text.strip()[:500]
                    print(f"  ✅ Symptoms found with selector: {selector}")
                    break

        if not details["symptoms"]:
            print("  ❌ No symptoms found")

        # Extract causes with better selectors
        print("🔍 Looking for causes content...")
        causes_selectors = [
            'h2:has-text("Causes") + p, h2:has-text("Causes") + div p',
            'h3:has-text("Causes") + p, h3:has-text("Causes") + div p',
            'h2:has-text("Aetiology") + p, h2:has-text("Aetiology") + div p',
            'h2:has-text("Risk factors") + p, h2:has-text("Risk factors") + div p',
            'section:has-text("Causes") p',
            'section:has-text("Aetiology") p',
            'section:has-text("Risk factors") p',
            '[data-section="causes"] p',
            'div:has(h2:text("Causes")) p, div:has(h3:text("Causes")) p',
        ]

        for selector in causes_selectors:
            causes_elem = page.locator(selector).first
            if await causes_elem.count() > 0:
                causes_text = await causes_elem.text_content()
                if causes_text and len(causes_text.strip()) > 20:
                    details["causes"] = causes_text.strip()[:500]
                    break

        # Extract treatments with better selectors
        print("🔍 Looking for treatment content...")
        treatment_selectors = [
            'h2:has-text("Treatment") + p, h2:has-text("Treatment") + div p',
            'h3:has-text("Treatment") + p, h3:has-text("Treatment") + div p',
            'h2:has-text("Management") + p, h2:has-text("Management") + div p',
            'h3:has-text("Management") + p, h3:has-text("Management") + div p',
            'h2:has-text("Therapy") + p, h2:has-text("Therapy") + div p',
            'section:has-text("Treatment") p',
            'section:has-text("Management") p',
            'section:has-text("Therapy") p',
            '[data-section="treatment"] p, [data-section="management"] p',
            'div:has(h2:text("Treatment")) p, div:has(h3:text("Management")) p',
        ]

        for selector in treatment_selectors:
            treatment_elem = page.locator(selector).first
            if await treatment_elem.count() > 0:
                treatment_text = await treatment_elem.text_content()
                if treatment_text and len(treatment_text.strip()) > 20:
                    details["treatments"] = treatment_text.strip()[:500]
                    break

        # Extract diagnosis with better selectors
        print("🔍 Looking for diagnosis content...")
        diagnosis_selectors = [
            'h2:has-text("Diagnosis") + p, h2:has-text("Diagnosis") + div p',
            'h3:has-text("Diagnosis") + p, h3:has-text("Diagnosis") + div p',
            'h2:has-text("Assessment") + p, h2:has-text("Assessment") + div p',
            'h2:has-text("Investigation") + p, h2:has-text("Investigation") + div p',
            'section:has-text("Diagnosis") p',
            'section:has-text("Assessment") p',
            'section:has-text("Investigation") p',
            '[data-section="diagnosis"] p, [data-section="assessment"] p',
            'div:has(h2:text("Diagnosis")) p, div:has(h3:text("Assessment")) p',
        ]

        for selector in diagnosis_selectors:
            diagnosis_elem = page.locator(selector).first
            if await diagnosis_elem.count() > 0:
                diagnosis_text = await diagnosis_elem.text_content()
                if diagnosis_text and len(diagnosis_text.strip()) > 20:
                    details["diagnosis"] = diagnosis_text.strip()[:500]
                    break

        # Log all found content sections
        print("📊 Content extraction summary:")
        for key, value in details.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {'Found' if value else 'Not found'}")

        # Enhanced fallback with better content filtering
        if not any(details.values()):
            print("🔄 No specific content found, trying enhanced fallback...")

            # Try to find any meaningful content that's not copyright/license text
            content_paragraphs = page.locator(
                """
                p:not(:has-text("copyright")):not(:has-text("licence")):not(:has-text("Clarity Informatics")):not(:has-text("End User Licence"))
            """
            )
            count = await content_paragraphs.count()
            print(f"  Found {count} non-copyright paragraphs to check")

            for i in range(min(5, count)):
                para = content_paragraphs.nth(i)
                text = await para.text_content()
                print(f"    Para {i+1}: {text[:100] if text else 'None'}...")

                # Skip obvious navigation or promotional text
                if text and len(text.strip()) > 30:
                    text_lower = text.lower()
                    if not any(
                        skip_word in text_lower
                        for skip_word in [
                            "navigation",
                            "menu",
                            "home",
                            "search",
                            "contact",
                            "about us",
                            "follow us",
                            "sign up",
                            "newsletter",
                            "cookies",
                            "privacy",
                        ]
                    ):
                        details["summary"] = text.strip()[:500]
                        print(f"  ✅ Using paragraph {i+1} as summary")
                        break

            # If still no content, try getting all headings to understand page structure
            if not details["summary"]:
                print("🔍 Examining page headings...")
                headings = page.locator("h1, h2, h3, h4")
                heading_count = await headings.count()
                print(f"  Found {heading_count} headings")

                for i in range(min(10, heading_count)):
                    heading = headings.nth(i)
                    text = await heading.text_content()
                    if text:
                        print(f"    H{i+1}: {text}")

                # Try to click on a content section if we find one
                content_links = page.locator(
                    'a:has-text("Background"), a:has-text("Management"), a:has-text("Scenario")'
                )
                if await content_links.count() > 0:
                    try:
                        print("  🌐 Trying to click on content section...")
                        await content_links.first.click()
                        await page.wait_for_load_state("networkidle")

                        # Try again to extract content after navigation
                        retry_paragraphs = page.locator(
                            'main p:not(:has-text("copyright")):not(:has-text("licence"))'
                        )
                        retry_count = await retry_paragraphs.count()
                        print(f"  Found {retry_count} paragraphs after navigation")

                        if retry_count > 0:
                            retry_text = await retry_paragraphs.first.text_content()
                            if retry_text and len(retry_text.strip()) > 30:
                                details["summary"] = retry_text.strip()[:500]
                                print("  ✅ Found content after navigation")
                    except Exception as e:
                        print(f"  ❌ Failed to navigate to content: {e}")

        return details

    except Exception as e:
        print(f"❌ Error extracting details from {url}: {e}")
        return {
            "summary": "Extraction failed",
            "symptoms": "",
            "causes": "",
            "treatments": "",
            "diagnosis": "",
            "management": "",
        }


async def scrape_nice_topics() -> Dict[str, Dict[str, str]]:
    """Scrape all NICE CKS topics with summaries and return as dictionary."""
    print("🔍 Starting NICE CKS topics scraper...")
    topics = {}

    async with async_playwright() as p:
        # Launch browser with stealth options
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
            ],
        )

        # Create context with realistic browser settings
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-GB",
            timezone_id="Europe/London",
            geolocation={"latitude": 51.5074, "longitude": -0.1278},  # London
            permissions=["geolocation"],
        )

        page = await context.new_page()

        # Add extra stealth measures
        await page.add_init_script(
            """
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {},
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en'],
            });
        """
        )

        # Set additional headers
        await page.set_extra_http_headers(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-GB,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
        )

        try:
            # Navigate to topics page
            print("📡 Navigating to NICE CKS topics page...")
            await page.goto("https://cks.nice.org.uk/topics/")

            # Handle overlays
            await page.wait_for_timeout(2000)

            try:
                accept_cookies = page.locator(
                    'button:has-text("Accept all cookies"), button:has-text("Accept"), button[aria-label*="Accept"]'
                )
                await accept_cookies.click(timeout=3000)
                print("✅ Accepted cookies")
            except:
                print("ℹ️  No cookie banner found")

            try:
                eula_accept = page.locator(
                    'button:has-text("Accept"), button:has-text("I agree"), button:has-text("Continue")'
                )
                await eula_accept.click(timeout=3000)
                print("✅ Accepted EULA")
            except:
                print("ℹ️  No EULA banner found")

            await page.wait_for_timeout(1000)

            # Wait for page to load completely
            await page.wait_for_load_state("networkidle")
            print("📄 Page loaded")

            # Find all topic links
            print("🔍 Looking for topic links...")

            # Try different selectors for topic links
            selectors = [
                'a[href*="/topics/"]:not([href="/topics/"])',  # Links containing /topics/ but not the main page
                ".topic-link",
                'a:has-text("Scenario")',  # Many topics have "Scenario" in them
                'ul li a[href*="/topics/"]',
            ]

            for selector in selectors:
                links = page.locator(selector)
                count = await links.count()
                print(f"📊 Found {count} links with selector: {selector}")

                if count > 0:
                    for i in range(count):
                        link = links.nth(i)

                        # Get title and URL
                        title = await link.text_content()
                        href = await link.get_attribute("href")

                        if title and href and title.strip():
                            title = title.strip()
                            full_url = (
                                href
                                if href.startswith("http")
                                else f"https://cks.nice.org.uk{href}"
                            )

                            # Only include unique topics (avoid duplicates)
                            if title not in topics:
                                topics[title] = {"url": full_url, "summary": ""}
                                if len(topics) % 50 == 0:
                                    print(f"📋 Scraped {len(topics)} topics so far...")
                    break  # Use first selector that works

            print(f"✅ Successfully scraped {len(topics)} topics")

        except Exception as e:
            print(f"❌ Error during scraping: {e}")

        finally:
            await browser.close()

    return topics


async def save_topics_to_file(topics: Dict[str, str], file_path: str = None) -> str:
    """Save topics dictionary to JSON file."""
    if file_path is None:
        file_path = Path(__file__).parent.parent.parent / "dat" / "nice-topics.json"

    print(f"💾 Saving {len(topics)} topics to {file_path}")

    # Ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    # Save as JSON
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)

    print(f"✅ Topics saved to {file_path}")
    return str(file_path)


async def scrape_and_save_topics() -> str:
    """Complete workflow: scrape topics and save to file."""
    print("🚀 Starting NICE CKS topics scraping workflow...")

    # Scrape topics
    topics = await scrape_nice_topics()

    if not topics:
        print("❌ No topics found!")
        return ""

    # Save to file
    file_path = await save_topics_to_file(topics)

    print(f"🎉 Scraping complete! {len(topics)} topics saved to {file_path}")
    return file_path


async def scrape_topic_details(limit: int = None) -> Dict[str, Dict[str, str]]:
    """Scrape detailed information from each NICE CKS topic."""
    print("🔍 Starting detailed topic scraping...")

    # Load existing topics
    topics = load_topics_from_file()
    if not topics:
        print("❌ No topics found. Run scrape_and_save_topics() first.")
        return {}

    detailed_topics = {}
    count = 0

    async with async_playwright() as p:
        # Launch browser with stealth options
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
            ],
        )

        # Create context with realistic browser settings
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-GB",
            timezone_id="Europe/London",
            geolocation={"latitude": 51.5074, "longitude": -0.1278},  # London
            permissions=["geolocation"],
        )

        page = await context.new_page()

        # Add extra stealth measures
        await page.add_init_script(
            """
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {},
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en'],
            });
        """
        )

        # Set additional headers
        await page.set_extra_http_headers(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-GB,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
        )

        # Add random delays to mimic human behavior
        await page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            for topic_name, topic_data in topics.items():
                if limit and count >= limit:
                    break

                print(f"📝 Scraping details for: {topic_name}")

                # Handle both dict and string formats
                if isinstance(topic_data, dict):
                    url = topic_data.get("url", "")
                else:
                    url = topic_data  # topic_data is the URL string

                if url:
                    details = await extract_topic_details(page, url)
                    detailed_topics[topic_name] = {"url": url, **details}
                    count += 1

                    if count % 10 == 0:
                        print(f"✅ Scraped {count} topics so far...")

                    # Random delay to mimic human behavior (1-3 seconds)
                    delay = random.uniform(1.0, 3.0)
                    await asyncio.sleep(delay)

        except Exception as e:
            print(f"❌ Error during detailed scraping: {e}")
        finally:
            await browser.close()

    print(f"🎉 Detailed scraping complete! {count} topics processed.")
    return detailed_topics


async def save_detailed_topics(
    topics: Dict[str, Dict[str, str]], file_path: str = None
) -> str:
    """Save detailed topics to JSON file."""
    if file_path is None:
        file_path = Path(__file__).parent.parent / "dat" / "nice-topics-detailed.json"

    print(f"💾 Saving {len(topics)} detailed topics to {file_path}")

    # Ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    # Save as JSON
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)

    print(f"✅ Detailed topics saved to {file_path}")
    return str(file_path)


async def scrape_and_save_detailed_topics(limit: int = None) -> str:
    """Complete workflow: scrape detailed topic information and save to file."""
    print("🚀 Starting detailed NICE CKS topics scraping workflow...")

    # Scrape detailed topics
    detailed_topics = await scrape_topic_details(limit)

    if not detailed_topics:
        print("❌ No detailed topics found!")
        return ""

    # Save to file
    file_path = await save_detailed_topics(detailed_topics)

    print(
        f"🎉 Detailed scraping complete! {len(detailed_topics)} topics saved to {file_path}"
    )
    return file_path


def load_topics_from_file(file_path: str = None) -> Dict[str, str]:
    """Load topics dictionary from JSON file."""
    if file_path is None:
        file_path = Path(__file__).parent.parent / "dat" / "nice-topics.json"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            topics = json.load(f)
        print(f"📖 Loaded {len(topics)} topics from {file_path}")
        return topics
    except FileNotFoundError:
        print(f"❌ Topics file not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"❌ Error reading topics file: {file_path}")
        return {}
