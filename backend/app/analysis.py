"""Explainable local assessments; these do not verify claims or infer personality."""
import re


def resume_quality(text: str, target: str) -> dict:
    lower = text.lower()
    checks = {
        'contact': bool(re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', lower)),
        'education': any(s in lower for s in ('education', 'university', 'bachelor', 'college')),
        'projects': 'project' in lower,
        'experience': any(s in lower for s in ('experience', 'internship', 'volunteer')),
        'skills': 'skill' in lower,
        'readable_length': 100 <= len(text.split()) <= 1500,
        'measurable_details': bool(re.search(r'\d+\s*(%|users|seconds|projects|customers)', lower)),
    }
    terms = set(re.findall(r'[a-z+#]{3,}', target.lower())) - {'developer', 'engineer', 'role', 'and', 'the', 'with'}
    matched = sorted(t for t in terms if t in lower)
    relevance = len(matched) / len(terms) if terms else None
    score = round(100 * sum(checks.values()) / len(checks), 1)
    if relevance is not None:
        score = round(score * .8 + relevance * 20, 1)
    missing = [key.replace('_', ' ') for key, value in checks.items() if not value]
    suggestions = [f"Improve {', '.join(missing[:3])}." if missing else 'Keep sections concise and consistently formatted.',
                   'Add project outcomes and evidence for skills relevant to ' + target + '.',
                   'Verify dates and claims manually; this assessment cannot establish factual accuracy.']
    return {'score': score, 'checks': checks, 'matched_terms': matched,
            'missing_terms': sorted(terms - set(matched)), 'suggestions': suggestions,
            'method': '80% section/length/evidence checks, 20% target keyword coverage (when target terms exist).'}


def communication(transcript: str, duration: float, segments: list | None = None) -> dict:
    words = re.findall(r"\b[\w']+\b", transcript.lower())
    if not words or duration <= 0:
        raise ValueError('Speech and positive duration are required.')
    fillers = sum(words.count(w) for w in ('um', 'uh', 'erm', 'hmm'))
    fillers += len(re.findall(r'\b(?:you know|i mean|sort of)\b', transcript.lower()))
    wpm = round(len(words) * 60 / duration, 1)
    pacing = max(0, 100 - max(0, 100 - wpm, wpm - 180))
    fluency = max(0, 100 - 400 * fillers / len(words))
    markers = re.findall(r'\b(first|second|finally|because|therefore|for example|in conclusion)\b', transcript.lower())
    pauses = None if segments is None else sum(
        max(0, b['start'] - a['end']) for a, b in zip(segments, segments[1:])
        if b['start'] - a['end'] >= 1)
    return {'score': round(.5 * pacing + .5 * fluency, 1), 'words': len(words),
            'words_per_minute': wpm, 'duration_seconds': round(duration, 1),
            'filler_count': fillers, 'pause_seconds': round(pauses, 1) if pauses is not None else None,
            'organization_markers': len(markers),
            'organization_note': 'Counts explicit sequencing, reasoning and example phrases; this is a transcript proxy, not a validated clarity judgment.',
            'method': '50% pacing (100–180 words/minute), 50% filler frequency. Pauses are descriptive only.',
            'suggestions': ['Use clear examples and a beginning, explanation, and conclusion.',
                            'Practise a steady pace and replace fillers with short pauses.'],
            'notice': 'Estimated speech metrics; no inference of honesty, confidence, or personality.'}
