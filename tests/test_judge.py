"""T-M4.10: judge_answer() against the real Gemini API -- a genuinely
faithful answer should score high, a genuinely unfaithful one (a claim
citing real chunks that say something else entirely) should score low."""
from app.evaluation import judge_answer
from app.generation import ContextSource, build_context
from app.generation.gemini import GeminiLLMProvider
from app.generation.schema import Claim, GeneratedAnswer


def _context():
    return build_context(
        [
            ContextSource(
                chunk_id="c1",
                document_title="Returns Policy",
                document_version=None,
                section_path="1",
                text="General items may be returned within 30 days of purchase with a receipt.",
            ),
            ContextSource(
                chunk_id="c2",
                document_title="Returns Policy",
                document_version=None,
                section_path="3.2",
                text="Clearance items marked final sale cannot be returned or exchanged.",
            ),
        ]
    )


def test_judge_scores_a_genuinely_faithful_answer_highly():
    context = _context()
    answer = GeneratedAnswer(
        answerable=True,
        summary="General items can be returned within 30 days with a receipt; clearance items are final sale.",
        claims=[
            Claim(statement="General items may be returned within 30 days with a receipt.", citation_numbers=[1]),
            Claim(statement="Clearance items marked final sale cannot be returned.", citation_numbers=[2]),
        ],
    )
    provider = GeminiLLMProvider()
    score = judge_answer("What is the return policy?", None, answer, context, provider)
    assert score.faithfulness >= 0.8
    assert score.citation_support_rate >= 0.8


def test_judge_scores_a_genuinely_unfaithful_answer_lowly():
    """Claim cites chunk [1] (the 30-day return window) but states
    something [1] never says at all -- a real unfaithfulness case, not a
    hypothetical one."""
    context = _context()
    answer = GeneratedAnswer(
        answerable=True,
        summary="All items, including clearance, can be returned within 90 days for store credit.",
        claims=[
            Claim(
                statement="All items including clearance can be returned within 90 days for store credit.",
                citation_numbers=[1],
            ),
        ],
    )
    provider = GeminiLLMProvider()
    score = judge_answer("What is the return policy?", None, answer, context, provider)
    assert score.faithfulness <= 0.3
    assert score.citation_support_rate <= 0.3


def test_judge_scores_a_correct_abstention_as_fully_correct_and_faithful():
    context = _context()
    answer = GeneratedAnswer(
        answerable=False,
        summary="The provided context does not mention employee discount percentages.",
        claims=[],
    )
    provider = GeminiLLMProvider()
    score = judge_answer(
        "What percentage employee discount applies to personal purchases?", None, answer, context, provider
    )
    assert score.correctness >= 0.8
    assert score.faithfulness >= 0.8


def test_judge_is_deterministic_at_temperature_zero():
    """Same input, same score -- required for T-M4.15's agreement
    measurement to compare against a fixed target, not a moving one."""
    context = _context()
    answer = GeneratedAnswer(
        answerable=True,
        summary="General items can be returned within 30 days with a receipt.",
        claims=[Claim(statement="General items may be returned within 30 days with a receipt.", citation_numbers=[1])],
    )
    provider = GeminiLLMProvider()
    score1 = judge_answer("What is the return policy?", None, answer, context, provider)
    score2 = judge_answer("What is the return policy?", None, answer, context, provider)
    assert score1.faithfulness == score2.faithfulness
    assert score1.correctness == score2.correctness
    assert score1.citation_support_rate == score2.citation_support_rate
