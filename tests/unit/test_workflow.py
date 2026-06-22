from unittest.mock import patch

import pytest
from google.adk.agents.llm_agent import LlmAgent
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from customer_support_agent.agent import app


async def mock_classifier_run_impl(self, *, ctx, node_input):
    if "track" in str(node_input).lower() or "shipping" in str(node_input).lower():
        classification = "shipping"
    else:
        classification = "unrelated"
    yield Event(output=classification)


async def mock_shipping_faq_run_impl(self, *, ctx, node_input):
    yield Event(output="FAQ Answer: Your package is on the way.")


@pytest.mark.asyncio
async def test_shipping_workflow_routing_shipping() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        app=app,
        session_service=session_service,
        auto_create_session=True,
    )

    query = "How do I track my package?"
    message = types.Content(parts=[types.Part.from_text(text=query)])

    original_run_impl = LlmAgent._run_impl

    async def dispatch_run_impl(self, *, ctx, node_input):
        if self.name == "classifier_agent":
            async for ev in mock_classifier_run_impl(
                self, ctx=ctx, node_input=node_input
            ):
                yield ev
        elif self.name == "shipping_faq_agent":
            async for ev in mock_shipping_faq_run_impl(
                self, ctx=ctx, node_input=node_input
            ):
                yield ev
        else:
            async for ev in original_run_impl(self, ctx=ctx, node_input=node_input):
                yield ev

    outputs = []
    with patch.object(LlmAgent, "_run_impl", dispatch_run_impl):
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=message,
        ):
            if event.output is not None:
                outputs.append(event.output)
            elif event.content is not None:
                text_parts = [p.text for p in (event.content.parts or []) if p.text]
                if text_parts:
                    outputs.append("".join(text_parts))

    assert "FAQ Answer: Your package is on the way." in outputs


@pytest.mark.asyncio
async def test_shipping_workflow_routing_unrelated() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        app=app,
        session_service=session_service,
        auto_create_session=True,
    )

    query = "What is the weather like today?"
    message = types.Content(parts=[types.Part.from_text(text=query)])

    original_run_impl = LlmAgent._run_impl

    async def dispatch_run_impl(self, *, ctx, node_input):
        if self.name == "classifier_agent":
            async for ev in mock_classifier_run_impl(
                self, ctx=ctx, node_input=node_input
            ):
                yield ev
        elif self.name == "shipping_faq_agent":
            async for ev in mock_shipping_faq_run_impl(
                self, ctx=ctx, node_input=node_input
            ):
                yield ev
        else:
            async for ev in original_run_impl(self, ctx=ctx, node_input=node_input):
                yield ev

    outputs = []
    with patch.object(LlmAgent, "_run_impl", dispatch_run_impl):
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=message,
        ):
            if event.output is not None:
                outputs.append(event.output)
            elif event.content is not None:
                text_parts = [p.text for p in (event.content.parts or []) if p.text]
                if text_parts:
                    outputs.append("".join(text_parts))

    # Should routing to decline node
    assert any(
        "I'm sorry, but I can only assist with questions related to shipping"
        in str(out)
        for out in outputs
    )
