import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src_python.nlu.pipeline import NLUComponent
from src_python.llm.manager import LLMManager

logger = logging.getLogger(__name__)


class NLUResult(BaseModel):
    """Structured result from LLM-based NLU processing."""
    intent: Optional[str] = None
    confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)


class ZeroShotNLU(NLUComponent):
    """
    Zero-shot NLU component using LLM (NVIDIA NIM / OpenRouter) 
    to extract intents and entities from user messages.
    """

    PROMPT_TEMPLATE = """You are an NLU engine for a chatbot. Extract the user's intent and entities from their message.

Available Intents: {intents}
Available Entities: {entities}

Analyze the user's message and return a JSON object with:
- "intent": the most likely intent from the list above, or null if no match
- "confidence": confidence score 0.0-1.0
- "entities": object mapping entity names to extracted values

Only extract entities that are explicitly mentioned. Return valid JSON only.

User message: {text}"""

    def __init__(
        self,
        intents: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        llm_manager: Optional[LLMManager] = None,
        **kwargs,
    ):
        """
        Args:
            intents: List of intent names to recognize
            entities: List of entity names to extract
            llm_manager: LLMManager instance for backend calls
            **kwargs: Additional configuration (temperature, etc.)
        """
        self.intents = intents or []
        self.entities = entities or []
        self.llm_manager = llm_manager
        self.temperature = kwargs.get("temperature", 0.1)

    def _build_prompt(self, text: str) -> str:
        """Build the prompt for the LLM."""
        return self.PROMPT_TEMPLATE.format(
            intents=", ".join(self.intents) if self.intents else "none",
            entities=", ".join(self.entities) if self.entities else "none",
            text=text,
        )

    def train(self, training_data: List[Dict[str, Any]], model_path: str) -> None:
        """
        Placeholder for training functionality.
        Zero-shot learning doesn't require training.
        """
        pass

    def load(self, model_path: str) -> bool:
        """
        Placeholder for loading a pre-trained model.
        Zero-shot learning doesn't require loading.
        """
        return True

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message and extract intents and entities using the LLM.

        Args:
            message: The input message containing the text to process.

        Returns:
            The processed message with extracted intents and entities.
        """
        if not message.get("text"):
            logger.warning("Message does not contain 'text' key. Skipping processing.")
            return message

        if not self.llm_manager:
            logger.warning("LLM Manager not available. Skipping NLU processing.")
            return message

        try:
            prompt = self._build_prompt(message.get("text"))
            result = self.llm_manager.complete(prompt, temperature=self.temperature)

            # Parse JSON response
            nlu_result = json.loads(result.strip())

            # Extract intent
            intent_value = nlu_result.get("intent")
            if intent_value and intent_value in self.intents:
                intent = {
                    "intent": intent_value,
                    "confidence": nlu_result.get("confidence", 1.0),
                }
                message["intent"] = intent
                message["intent_ranking"] = [intent]
            else:
                message["intent"] = {"intent": None, "confidence": 0.0}
                message["intent_ranking"] = []

            # Extract and filter entities
            entities = nlu_result.get("entities", {})
            # Only keep entities that are in our allowed list
            allowed_entities = {k: v for k, v in entities.items() if k in self.entities}
            message["entities"] = allowed_entities

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM NLU response as JSON: {e}")
            message["intent"] = {"intent": None, "confidence": 0.0}
            message["intent_ranking"] = []
            message["entities"] = {}
        except Exception as e:
            logger.error(f"Error processing message with LLM NLU: {e}", exc_info=True)
            message["intent"] = {"intent": None, "confidence": 0.0}
            message["intent_ranking"] = []
            message["entities"] = {}

        return message