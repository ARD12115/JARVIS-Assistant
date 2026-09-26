from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy


@dataclass
class ApiDetailsModel:
    url: str
    request_type: str
    headers: List[Dict[str, str]]
    is_json: bool = False
    json_data: str = "{}"

    def get_headers(self) -> Dict[str, str]:
        headers = {}
        for header in self.headers:
            headers[header["headerKey"]] = header["headerValue"]
        return headers


@dataclass
class ParameterModel:
    name: str
    required: bool = False
    type: Optional[str] = None
    prompt: Optional[str] = None


@dataclass
class IntentModel:
    name: str
    intent_id: str
    speech_response: str
    user_defined: bool = True
    api_trigger: bool = False
    api_details: Optional[ApiDetailsModel] = None
    parameters: List[ParameterModel] = field(default_factory=list)


@dataclass
class UserMessage:
    thread_id: str
    text: str
    context: Dict = field(default_factory=dict)
    channel: str = "rest"

    def to_dict(self) -> Dict:
        return {
            "thread_id": self.thread_id,
            "text": self.text,
            "channel": self.channel,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserMessage":
        return cls(
            thread_id=data["thread_id"],
            text=data["text"],
            context=data["context"],
            channel=data.get("channel", "rest"),
        )


class State:
    """Conversation state for a thread."""

    def __init__(
        self,
        thread_id: str,
        input_text: str = "",
        context: Optional[Dict] = None,
        intent: Optional[Dict] = None,
        extracted_parameters: Optional[Dict] = None,
        missing_parameters: Optional[List[str]] = None,
        complete: bool = False,
        speech_response: Optional[List[str]] = None,
        current_node: str = "",
        parameters: Optional[List[Dict[str, Any]]] = None,
        owner: str = "",
        date: Optional[str] = None,
        nlu: Optional[Dict] = None,
    ):
        self.thread_id = thread_id
        self.input_text = input_text
        self.context = context or {}
        self.intent = intent or {}
        self.nlu = nlu or {}
        self.extracted_parameters = extracted_parameters or {}
        self.missing_parameters = missing_parameters or []
        self.complete = complete
        self.speech_response = speech_response or []
        self.current_node = current_node
        self.parameters = parameters or []
        self.owner = owner
        self.date = date or datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict) -> "State":
        return cls(
            thread_id=data.get("thread_id", ""),
            input_text=data.get("input_text", ""),
            context=data.get("context", {}),
            intent=data.get("intent", {}),
            extracted_parameters=data.get("extracted_parameters", {}),
            missing_parameters=data.get("missing_parameters", []),
            complete=data.get("complete", False),
            speech_response=data.get("speech_response", []),
            current_node=data.get("current_node", ""),
            parameters=data.get("parameters", []),
            owner=data.get("owner", ""),
            date=data.get("date"),
            nlu=data.get("nlu"),
        )

    def to_dict(self) -> Dict:
        return {
            "thread_id": self.thread_id,
            "input_text": self.input_text,
            "context": self.context,
            "intent": self.intent,
            "nlu": self.nlu,
            "extracted_parameters": self.extracted_parameters,
            "missing_parameters": self.missing_parameters,
            "complete": self.complete,
            "speech_response": self.speech_response,
            "current_node": self.current_node,
            "parameters": self.parameters,
            "owner": self.owner,
            "date": self.date,
        }

    def clone(self):
        return deepcopy(self)

    def reset(self):
        self.complete = False
        self.intent = {}
        self.missing_parameters = []
        self.extracted_parameters = {}
        self.parameters = []
        self.current_node = ""
        self.speech_response = []