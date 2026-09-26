import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from jinja2 import Template

from src_python.nlu.pipeline import NLUPipeline
from src_python.nlu.zero_shot import ZeroShotNLU
from src_python.dialogue.models import (
    IntentModel,
    ParameterModel,
    UserMessage,
    State,
    ApiDetailsModel,
)
from src_python.llm.manager import LLMManager
from src_python.memory.session import SessionMemory
from src_python.config import Config

logger = logging.getLogger(__name__)


class DialogueManagerException(Exception):
    pass


class DialogueManager:
    """
    Dialogue Manager that processes user messages through NLU pipeline
    and manages conversation state, intent handling, and API triggers.
    """

    def __init__(
        self,
        session_memory: SessionMemory,
        intents: List[IntentModel],
        nlu_pipeline: NLUPipeline,
        fallback_intent_id: str,
        intent_confidence_threshold: float,
        llm_manager: Optional[LLMManager] = None,
    ):
        self.session_memory = session_memory
        self.nlu_pipeline = nlu_pipeline
        self.intents = {
            intent.intent_id: intent for intent in intents
        }
        self.fallback_intent_id = fallback_intent_id
        self.confidence_threshold = intent_confidence_threshold
        self.llm_manager = llm_manager

    @classmethod
    def from_config(cls, config: Config, llm_manager: Optional[LLMManager] = None):
        """Initialize DialogueManager with configuration."""
        # Load intents from config/admin
        intents = cls._load_intents()
        
        # Create NLU pipeline
        nlu_pipeline = cls._create_nlu_pipeline(intents, llm_manager)
        
        # Get configuration
        fallback_intent_id = "fallback"
        intent_confidence_threshold = 0.5
        
        session_memory = SessionMemory(config.db_path)

        return cls(
            session_memory=session_memory,
            intents=intents,
            nlu_pipeline=nlu_pipeline,
            fallback_intent_id=fallback_intent_id,
            intent_confidence_threshold=intent_confidence_threshold,
            llm_manager=llm_manager,
        )

    @staticmethod
    def _load_intents() -> List[IntentModel]:
        """Load intents from configuration."""
        # Default intents for JARVIS
        return [
            IntentModel(
                name="Get Time",
                intent_id="get_time",
                speech_response="The current time is {{ parameters.timezone }}.",
                user_defined=False,
                parameters=[
                    ParameterModel(
                        name="timezone",
                        required=False,
                        type="timezone",
                        prompt="Which timezone would you like the time for?",
                    )
                ],
            ),
            IntentModel(
                name="Web Search",
                intent_id="web_search",
                speech_response="Here are the search results for {{ parameters.query }}.",
                user_defined=False,
                parameters=[
                    ParameterModel(
                        name="query",
                        required=True,
                        type="free_text",
                        prompt="What would you like me to search for?",
                    )
                ],
            ),
            IntentModel(
                name="File Operations",
                intent_id="file_ops",
                speech_response="File operation completed.",
                user_defined=False,
                parameters=[
                    ParameterModel(
                        name="operation",
                        required=True,
                        type="file_operation",
                        prompt="What file operation would you like to perform?",
                    ),
                    ParameterModel(
                        name="path",
                        required=True,
                        type="file_path",
                        prompt="What is the file path?",
                    ),
                ],
            ),
            IntentModel(
                name="Weather",
                intent_id="weather",
                speech_response="The weather in {{ parameters.location }} is {{ result.weather }}.",
                user_defined=False,
                api_trigger=True,
                parameters=[
                    ParameterModel(
                        name="location",
                        required=True,
                        type="location",
                        prompt="Which location would you like the weather for?",
                    )
                ],
            ),
            IntentModel(
                name="Fallback",
                intent_id="fallback",
                speech_response="I'm not sure how to help with that. Could you rephrase or try asking about time, weather, search, or files?",
                user_defined=False,
            ),
        ]

    @staticmethod
    def _create_nlu_pipeline(
        intents: List[IntentModel], 
        llm_manager: Optional[LLMManager]
    ) -> NLUPipeline:
        """Create NLU pipeline with zero-shot LLM component."""
        intent_ids = [intent.intent_id for intent in intents]
        entity_types = []
        for intent in intents:
            for param in intent.parameters:
                if param.type:
                    entity_types.append(param.type)
        
        zero_shot = ZeroShotNLU(
            intents=intent_ids,
            entities=list(set(entity_types)),
            llm_manager=llm_manager,
        )
        
        return NLUPipeline([zero_shot])

    def update_model(self, models_dir: str) -> bool:
        """Signal hook to be called after training is completed."""
        ok = self.nlu_pipeline.load(models_dir)
        if not ok:
            self.nlu_pipeline = None
        logger.info("NLU Pipeline models updated")
        return ok

    async def process(self, message: UserMessage) -> State:
        """
        Single entry point to process the user message.

        :param message: UserMessage instance containing the request data.
        :return: current state of the conversation including the bot response
        """
        if self.nlu_pipeline is None:
            raise DialogueManagerException(
                "NLU pipeline is not initialized. Please build the models."
            )

        # Step 1: Get current state from session memory
        current_state = await self._get_or_create_state(message.thread_id)
        current_state.input_text = message.text
        current_state.context = {**current_state.context, **message.context}

        try:
            # Step 2: Process through NLU pipeline
            nlu_input = {
                "text": message.text,
                "context": current_state.context,
            }
            nlu_result = self.nlu_pipeline.process(nlu_input)

            # Step 3: Get intent ID and confidence
            query_intent_id, _ = self._get_intent_id_and_confidence(
                current_state, nlu_result
            )

            # Step 4: Retrieve the intent object
            query_intent = self._get_intent(query_intent_id)
            if query_intent is None:
                query_intent = self._get_fallback_intent()

            current_state.nlu = {
                "entities": nlu_result.get("entities"),
                "intent": nlu_result.get("intent"),
            }

            # Check if intent changed
            active_intent_id = current_state.intent.get("id") if current_state.intent else None
            if active_intent_id and query_intent_id != active_intent_id:
                active_intent = self._get_intent(active_intent_id)
            else:
                active_intent = query_intent

            # Step 5: Process the intent
            current_state, active_intent = self._process_intent(
                query_intent,
                active_intent,
                current_state,
            )
            current_state.intent = {"id": active_intent.intent_id}

            # Step 6: Handle API trigger if the intent is complete
            if current_state.complete:
                current_state = await self._handle_api_trigger(
                    active_intent, current_state
                )

            logger.debug(
                f"Processed input: {current_state.thread_id}",
                extra=current_state.to_dict(),
            )

            # Step 7: Save the state
            await self._save_state(message.thread_id, current_state)

            return current_state

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            raise

    def _get_intent_id_and_confidence(
        self, current_state: State, nlu_result: Dict
    ) -> Tuple[str, float]:
        """Determine the intent ID and confidence based on the request input."""
        input_text = current_state.input_text
        if input_text.startswith("/"):
            intent_id = input_text.split("/")[1]
            confidence = 1.0
        else:
            predicted = nlu_result.get("intent", {})
            if predicted.get("confidence", 0) < self.confidence_threshold:
                return self.fallback_intent_id, 1.0
            else:
                return predicted.get("intent", self.fallback_intent_id), predicted.get("confidence", 0)
        return intent_id, confidence

    def _get_intent(self, intent_id: str) -> Optional[IntentModel]:
        """Retrieve the intent object by its ID."""
        return self.intents.get(intent_id)

    def _get_fallback_intent(self) -> IntentModel:
        """Retrieve the fallback intent."""
        return self.intents[self.fallback_intent_id]

    def _process_intent(
        self,
        query_intent: IntentModel,
        active_intent: IntentModel,
        current_state: State,
    ) -> Tuple[State, IntentModel]:
        """Process the intent and update the result model with extracted parameters."""
        # Cancel intent should cancel active intent and reset chat model
        if query_intent.intent_id == "cancel":
            active_intent = query_intent
            current_state.complete = True
            current_state.parameters = []
            current_state.extracted_parameters = {}
            current_state.missing_parameters = []
            current_state.current_node = ""
            return current_state, active_intent

        parameters = active_intent.parameters

        if parameters:
            # Get entities from NLU pipeline result
            extracted_entities = current_state.nlu.get("entities", {})

            # Group entities by type
            entities_by_type = {}
            for entity_name, entity_value in extracted_entities.items():
                if entity_name not in entities_by_type:
                    entities_by_type[entity_name] = []
                entities_by_type[entity_name].append(entity_value)

            # Populate parameters if not already populated
            if len(current_state.parameters) == 0:
                for param in parameters:
                    current_state.parameters.append(
                        {
                            "name": param.name,
                            "type": param.type,
                            "required": param.required,
                        }
                    )

            # Match extracted entities with parameters based on type
            for param in parameters:
                # For free_text parameters being prompted
                if (
                    param.type == "free_text"
                    and current_state.current_node == param.name
                ):
                    current_state.extracted_parameters[param.name] = (
                        current_state.input_text
                    )
                    continue
                else:
                    # Get all entities of matching type
                    if param.type in entities_by_type and entities_by_type[param.type]:
                        # Take the next available entity of this type
                        current_state.extracted_parameters[param.name] = (
                            entities_by_type[param.type].pop(0)
                        )

            # Handle missing parameters
            current_state = self._handle_missing_parameters(parameters, current_state)

        # Check if there are no missing parameters to mark the intent as complete
        current_state.complete = not current_state.missing_parameters
        return current_state, active_intent

    def _handle_missing_parameters(
        self, parameters: List[ParameterModel], current_state: State
    ) -> State:
        """Handle missing parameters in the result model."""
        missing_parameters = []
        current_state.missing_parameters = []
        current_state.current_node = ""
        current_state.speech_response = []

        for parameter in parameters:
            if (
                parameter.required
                and parameter.name not in current_state.extracted_parameters
            ):
                current_state.missing_parameters.append(parameter.name)
                missing_parameters.append(parameter)

        if missing_parameters:
            current_node = missing_parameters[0]
            current_state.current_node = current_node.name
            current_state.speech_response = [
                current_node.prompt or f"Please provide {current_node.name}"
            ]
        return current_state

    async def _handle_api_trigger(
        self, intent: IntentModel, current_state: State
    ) -> State:
        """Handle API trigger if the intent requires it."""
        if intent.api_trigger and intent.api_details:
            try:
                result = await self._call_intent_api(intent, current_state)
                template = Template(
                    intent.speech_response,
                    undefined=SilentUndefined,
                    enable_async=True,
                )
                rendered_text = await template.render_async(
                    context=current_state.context,
                    parameters=current_state.extracted_parameters,
                    result=result,
                )

                current_state.speech_response = [
                    msg for msg in split_sentence(rendered_text)
                ]

            except DialogueManagerException as e:
                logger.warning(f"API call failed: {e}")
                current_state.speech_response = [
                    "Service is not available. Please try again later."
                ]
        else:
            template = Template(
                intent.speech_response,
                undefined=SilentUndefined,
                enable_async=True,
            )
            rendered_text = await template.render_async(
                context=current_state.context,
                parameters=current_state.extracted_parameters,
            )
            current_state.speech_response = [
                msg for msg in split_sentence(rendered_text)
            ]
        return current_state

    async def _call_intent_api(self, intent: IntentModel, current_state: State) -> Any:
        """Call the API associated with the intent."""
        api_details = intent.api_details
        headers = api_details.get_headers()
        url_template = Template(api_details.url, undefined=SilentUndefined)
        rendered_url = url_template.render(
            context=current_state.context, parameters=current_state.extracted_parameters
        )
        if api_details.is_json:
            request_template = Template(
                api_details.json_data, undefined=SilentUndefined
            )
            request_json = request_template.render(
                context=current_state.context,
                parameters=current_state.extracted_parameters,
            )
            parameters = json.loads(request_json)
        else:
            parameters = current_state.extracted_parameters

        # For now, use LLM to call APIs (placeholder for actual API client)
        # In production, use a proper HTTP client
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    api_details.request_type,
                    rendered_url,
                    headers=headers,
                    json=parameters if api_details.is_json else None,
                    data=parameters if not api_details.is_json else None,
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.warning(f"API call failed: {e}")
            raise DialogueManagerException("API call failed")

    async def _get_or_create_state(self, thread_id: str) -> State:
        """Get existing state or create new one from session memory."""
        # Try to load from session memory
        history = self.session_memory.get_history(limit=1, session_id=thread_id)
        if history:
            # Restore state from last message
            last_msg = history[0]
            try:
                state = State.from_dict({
                    "thread_id": thread_id,
                    "context": last_msg.context or {},
                    "intent": last_msg.intent or {},
                    "extracted_parameters": last_msg.extracted_parameters or {},
                    "missing_parameters": last_msg.missing_parameters or [],
                    "complete": last_msg.complete or False,
                    "speech_response": last_msg.speech_response or [],
                    "current_node": last_msg.current_node or "",
                    "parameters": last_msg.parameters or [],
                })
                return state
            except Exception:
                # If restoration fails, fall back to building state from last message
                pass
        
        # Fallback: build state from last message or create new
        history = self.session_memory.get_history(limit=1, session_id=thread_id)
        if history:
            # Build state from last message
            last_msg = history[0]
            state = State(
                thread_id=thread_id,
                context={},
                intent={},
                extracted_parameters={},
                missing_parameters=[],
                complete=False,
                speech_response=[],
                current_node="",
                parameters=[],
            )
            return state
        
        return State(thread_id=thread_id)

    async def _save_state(self, thread_id: str, state: State) -> None:
        """Save state to session memory."""
        # Save the assistant response as a message
        if state.speech_response:
            for msg in state.speech_response:
                self.session_memory.add_message(
                    session_id=thread_id,
                    role="assistant",
                    content=msg,
                    tool_calls="[]",
                    tool_results="[]",
                    latency_ms=None,
                    backend_used="dialogue_manager",
                )


class SilentUndefined:
    """Jinja2 undefined handler that returns empty string for undefined variables."""
    def __init__(self, hint=None, obj=None, name=None, exc=None):
        self._hint = hint
        self._obj = obj
        self._name = name
        self._exc = exc

    def __str__(self):
        return ""

    def __bool__(self):
        return False

    def __getattr__(self, name):
        return SilentUndefined()

    def __call__(self, *args, **kwargs):
        return SilentUndefined()

    def __getitem__(self, key):
        return SilentUndefined()


def split_sentence(text: str) -> List[str]:
    """Split text into sentences for streaming."""
    import re
    # Simple sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]