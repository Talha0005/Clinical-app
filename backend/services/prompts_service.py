"""
Prompts management service for DigiClinic
Handles loading, saving, and managing editable prompts from JSON file storage
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)
try:
    from services.audit import log_audit
except Exception:
    # Fallback if audit module is unavailable during early imports
    def log_audit(**kwargs):  # type: ignore
        pass


class PromptsService:
    """Service for managing editable prompts stored in JSON files"""

    def __init__(self, prompts_file: str = None):
        """Initialize prompts service

        Args:
            prompts_file: Path to prompts JSON file.
                If None, uses default location.
        """
        if prompts_file is None:
            # Default to dat/prompts.json in backend directory
            backend_dir = Path(__file__).parent.parent
            prompts_file = backend_dir / "dat" / "prompts.json"

        self.prompts_file = Path(prompts_file)
        self.prompts_cache: Dict[str, Any] = {}
        self.last_loaded: Optional[datetime] = None

        # Ensure the directory exists
        self.prompts_file.parent.mkdir(parents=True, exist_ok=True)

        # Load prompts on initialization
        self.load_prompts()

    def load_prompts(self) -> Dict[str, Any]:
        """Load prompts from JSON file"""
        try:
            if not self.prompts_file.exists():
                logger.warning(f"Prompts file not found: {self.prompts_file}")
                return self._create_default_prompts()

            with open(self.prompts_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.prompts_cache = data
            self.last_loaded = datetime.now()
            count = len(data.get("prompts", {}))
            logger.info(
                "Loaded %d prompts from %s",
                count,
                self.prompts_file,
            )
            return data

        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON in prompts file %s: %s",
                self.prompts_file,
                e,
            )
            return self._create_default_prompts()
        except PermissionError as e:
            logger.error(
                "Permission denied reading prompts file %s: %s",
                self.prompts_file,
                e,
            )
            return self._create_default_prompts()
        except FileNotFoundError as e:
            logger.error(f"Prompts file not found {self.prompts_file}: {e}")
            return self._create_default_prompts()
        except Exception as e:
            logger.error(f"Unexpected error loading prompts: {e}")
            return self._create_default_prompts()

    def save_prompts(self) -> bool:
        """Save prompts to JSON file using atomic operations"""
        try:
            # Update metadata
            self.prompts_cache["metadata"]["last_updated"] = datetime.now().isoformat()
            self.prompts_cache["metadata"]["total_prompts"] = len(
                self.prompts_cache.get("prompts", {})
            )

            # Use atomic write (write to temp file, then rename)
            temp_file = self.prompts_file.with_suffix(".tmp")

            # Write to temporary file first
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.prompts_cache, f, indent=2, ensure_ascii=False)

            # Atomic rename (this is atomic on most filesystems)
            temp_file.replace(self.prompts_file)

            logger.info(f"Saved prompts to {self.prompts_file}")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Error serializing prompts to JSON: {e}")
            return False
        except PermissionError as e:
            logger.error(f"Permission denied writing prompts file: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving prompts: {e}")
            return False

    def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific prompt by ID"""
        prompts = self.prompts_cache.get("prompts", {})
        return prompts.get(prompt_id)

    def get_active_prompt(self, prompt_id: str) -> Optional[str]:
        """Get the content of an active prompt by ID"""
        prompt = self.get_prompt(prompt_id)
        if prompt and prompt.get("is_active", False):
            return prompt.get("content")
        return None

    def build_enhanced_system_prompt(
        self,
        base_id: str = "system_prompt",
        patient_snapshot: Optional[str] = None,
    ) -> str:
        """Return system prompt enhanced with optional patient snapshot."""
        base = self.get_active_prompt(base_id) or "You are a helpful medical assistant."
        if patient_snapshot:
            return (
                base
                + "\n\n---\nPatient Snapshot (for context):\n"
                + patient_snapshot
                + "\n---\n"
            )
        return base

    def get_all_prompts(self) -> Dict[str, Any]:
        """Get all prompts"""
        return self.prompts_cache.get("prompts", {})

    def get_prompts_by_category(self, category: str) -> Dict[str, Any]:
        """Get all prompts in a specific category"""
        prompts = self.get_all_prompts()
        return {
            prompt_id: prompt_data
            for prompt_id, prompt_data in prompts.items()
            if prompt_data.get("category") == category
        }

    def update_prompt(
        self,
        prompt_id: str,
        updates: Dict[str, Any],
        user_id: str = None,
    ) -> bool:
        """Update a specific prompt

        Args:
            prompt_id: ID of prompt to update
            updates: Dictionary of fields to update
            user_id: ID of user making the change (for audit logging)

        Returns:
            True if successful, False otherwise
        """
        try:
            prompts = self.prompts_cache.get("prompts", {})

            if prompt_id not in prompts:
                logger.error(f"Prompt not found: {prompt_id}")
                return False

            # Store original prompt for audit logging
            # Keep a shallow copy for potential future audit diffing
            original_prompt = prompts[prompt_id].copy()  # noqa: F841

            # Update the prompt
            prompt = prompts[prompt_id]

            # Update allowed fields
            allowed_fields = [
                "name",
                "description",
                "content",
                "category",
                "is_active",
            ]
            changed_fields = {}
            for field, value in updates.items():
                if field in allowed_fields and prompt.get(field) != value:
                    changed_fields[field] = {
                        "old": prompt.get(field),
                        "new": value,
                    }
                    prompt[field] = value

            # Update version and timestamp
            old_version = prompt.get("version", 1)
            prompt["version"] = old_version + 1
            prompt["updated_at"] = datetime.now().isoformat()

            # Audit logging for medical compliance
            if changed_fields:
                logger.info(
                    "AUDIT: Prompt %s updated by %s - v%s->%s - fields: %s",
                    prompt_id,
                    user_id or "unknown",
                    old_version,
                    prompt["version"],
                    list(changed_fields.keys()),
                )

                # Log content changes for medical prompts specifically
                if (
                    prompt.get("category") in ["medical", "system"]
                    and "content" in changed_fields
                ):
                    logger.warning(
                        "MEDICAL_AUDIT: Critical prompt change - "
                        "Prompt: %s, User: %s, v%s",
                        prompt_id,
                        user_id or "unknown",
                        prompt["version"],
                    )

                # Persist audit to file
                try:
                    critical = (
                        prompt.get("category") in ["medical", "system"]
                        and "content" in changed_fields
                    )
                    log_audit(
                        actor=user_id or "unknown",
                        event_type="prompt_update",
                        target=prompt_id,
                        details={
                            "changed_fields": list(changed_fields.keys()),
                            "version": prompt["version"],
                            "category": prompt.get("category"),
                            "critical": bool(critical),
                        },
                    )
                except Exception:
                    pass

            # Save to file
            return self.save_prompts()

        except Exception as e:
            logger.error(f"Error updating prompt {prompt_id}: {e}")
            return False

    def create_prompt(self, prompt_data: Dict[str, Any]) -> bool:
        """Create a new prompt

        Args:
            prompt_data: Prompt data including id, name, description,
                content, etc.

        Returns:
            True if successful, False otherwise
        """
        try:
            prompt_id = prompt_data.get("id")
            if not prompt_id:
                logger.error("Prompt ID is required")
                return False

            prompts = self.prompts_cache.get("prompts", {})

            if prompt_id in prompts:
                logger.error(f"Prompt already exists: {prompt_id}")
                return False

            # Create new prompt with required fields
            new_prompt = {
                "id": prompt_id,
                "name": prompt_data.get("name", ""),
                "description": prompt_data.get("description", ""),
                "category": prompt_data.get("category", "custom"),
                "content": prompt_data.get("content", ""),
                "version": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_active": prompt_data.get("is_active", True),
            }

            prompts[prompt_id] = new_prompt

            return self.save_prompts()

        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            return False

    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt

        Args:
            prompt_id: ID of prompt to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            prompts = self.prompts_cache.get("prompts", {})

            if prompt_id not in prompts:
                logger.error(f"Prompt not found: {prompt_id}")
                return False

            del prompts[prompt_id]

            return self.save_prompts()

        except Exception as e:
            logger.error(f"Error deleting prompt {prompt_id}: {e}")
            return False

    def _create_default_prompts(self) -> Dict[str, Any]:
        """Create default prompts structure"""
        default_prompts = {
            "prompts": {
                "system_prompt": {
                    "id": "system_prompt",
                    "name": "System Prompt",
                    "description": (
                        "Main system prompt used for conversation " "initialization"
                    ),
                    "category": "system",
                    "content": (
                        "You are Dr. Hervix, a digital GP consultant for the "
                        "NHS DigiClinic platform."
                    ),
                    "version": 1,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "is_active": True,
                }
            },
            "metadata": {
                "version": 1,
                "last_updated": datetime.now().isoformat(),
                "total_prompts": 1,
            },
        }

        self.prompts_cache = default_prompts
        self.save_prompts()
        return default_prompts


# Global prompts service instance
prompts_service = PromptsService()
