"""Hypothetical Document Embeddings.

https://arxiv.org/abs/2212.10496
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from langchain_core.callbacks import CallbackManagerForChainRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import BasePromptTemplate

from langchain.chains.base import Chain
from langchain.chains.hyde.prompts import PROMPT_MAP
from langchain.chains.llm import LLMChain


class HypotheticalDocumentEmbedder(Chain, Embeddings):
    """Generate hypothetical document for query, and then embed that.

    Based on https://arxiv.org/abs/2212.10496
    """

    base_embeddings: Embeddings
    llm_chain: LLMChain

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"

    @property
    def input_keys(self) -> List[str]:
        """Input keys for Hyde's LLM chain."""
        return self.llm_chain.input_keys

    @property
    def output_keys(self) -> List[str]:
        """Output keys for Hyde's LLM chain."""
        return self.llm_chain.output_keys

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Call the base embeddings."""
        return self.base_embeddings.embed_documents(texts)

    def combine_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Combine embeddings into final embeddings."""
        return list(np.array(embeddings).mean(axis=0))

    def embed_query(self, text: str) -> List[float]:
        """Generate a hypothetical document and embedded it."""
        var_name = self.llm_chain.input_keys[0]
        result = self.llm_chain.generate([{var_name: text}])
        documents = [generation.text for generation in result.generations[0]]
        embeddings = self.embed_documents(documents)
        return self.combine_embeddings(embeddings)

    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, str]:
        """Call the internal llm chain."""
        _run_manager = run_manager or CallbackManagerForChainRun.get_noop_manager()
        return self.llm_chain(inputs, callbacks=_run_manager.get_child())

    @classmethod
    def from_llm(
        cls,
        llm: BaseLanguageModel,
        base_embeddings: Embeddings,
        prompt_key: Optional[str] = None,
        custom_prompt: Optional[BasePromptTemplate] = None,
        **kwargs: Any,
    ) -> HypotheticalDocumentEmbedder:
        """Load and use LLMChain with either a specific prompt key or custom prompt."""
        if custom_prompt is not None:
            prompt = custom_prompt
        elif prompt_key is not None and prompt_key in PROMPT_MAP:
            prompt = PROMPT_MAP[prompt_key]
        else:
            raise ValueError(
                f"Must specify prompt_key if custom_prompt not provided. Should be one "
                f"of {list(PROMPT_MAP.keys())}."
            )

        llm_chain = LLMChain(llm=llm, prompt=prompt)
        return cls(base_embeddings=base_embeddings, llm_chain=llm_chain, **kwargs)

    @property
    def _chain_type(self) -> str:
        return "hyde_chain"
