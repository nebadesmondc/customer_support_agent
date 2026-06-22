# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.workflow import node, START, Workflow
from google.adk.agents.context import Context
from google.genai import types

try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
except Exception:
    # Fail gracefully on import if ADC credentials are not configured yet
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "mock-project-id")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

# Shared Gemini model
model = Gemini(
    model="gemini-flash-latest",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# 1. Helper Classifier Agent
classifier_agent = Agent(
    name="classifier_agent",
    model=model,
    instruction=(
        "You are an AI classifier for a shipping company customer support line.\n"
        "Your task is to classify whether the user's query is related to shipping (rates, tracking, delivery, returns) or unrelated.\n"
        "Respond with exactly one of the following words:\n"
        "- 'shipping' if it is related to shipping (rates, tracking, delivery, returns, packaging, carrier options, delivery time, shipping cost, address changes, package status, etc.)\n"
        "- 'unrelated' if the query is unrelated to shipping (e.g. general conversation, weather, jokes, programming, politics, or other non-shipping topics).\n"
        "Do not include any other text or punctuation."
    ),
)


# 2. Classifier node to execute helper agent and route
@node(rerun_on_resume=True)
async def classifier(ctx: Context, node_input: str) -> str:
    result = await ctx.run_node(classifier_agent, node_input)
    res_str = str(result).strip().lower()
    if "shipping" in res_str:
        ctx.route = "shipping"
    else:
        ctx.route = "unrelated"
    return node_input


# 3. Shipping FAQ Agent
shipping_faq_agent = Agent(
    name="shipping_faq_agent",
    model=model,
    instruction=(
        "You are a helpful, polite, and enthusiastic shipping company customer support representative.\n"
        "Answer the user's shipping-related questions (rates, tracking, delivery, returns) accurately and clearly.\n"
        "Specifically, when answering questions about shipping rates, be extremely playful and enthusiastic, use lots of fun emojis, and highlight our amazing **FREE SHIPPING** threshold for orders over $50! 🚚💨✨\n"
        "If you do not have enough information to answer a specific tracking question, ask the user to provide their tracking number."
    ),
)


# 4. Decline node
@node
async def decline_node(ctx: Context, node_input: str) -> str:
    return (
        "I'm sorry, but I can only assist with questions related to shipping (such as rates, tracking, delivery, and returns). "
        "Please let me know if you have a shipping-related inquiry!"
    )


# 5. Define workflow
root_agent = Workflow(
    name="customer_support_agent",
    edges=[
        (START, classifier),
        (classifier, {"shipping": shipping_faq_agent, "unrelated": decline_node}),
    ],
)

# 6. Define App
app = App(
    root_agent=root_agent,
    name="customer_support_agent",
)
