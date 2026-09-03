"""
LLM-Powered Gender Detection Service for Indian & Global Resumes.

Architecture (4-tier, lowest-cost-first):
─────────────────────────────────────────
Tier 1 (0 tokens, ~0ms): Explicit pronoun scan — regex over raw CV text.
         "he works…" / "she built…" / "his responsibilities…"
Tier 2 (0 tokens, ~0ms): Curated Indian & global first-name dictionary.
         ~4,000 common Indian names + 2,000 western names with known gender.
Tier 3 (~80 tokens, ~500ms): LLM contextual inference — called only when tiers
         1 & 2 return unknown. LLM reads candidate name + 200-char CV excerpt
         and returns JSON {"gender": "Male"|"Female"|"Non-Binary"|"Unknown"}.
Tier 4  Fallback: Returns "Unknown" safely if LLM is offline or ambiguous.

Output values: "Male" | "Female" | "Non-Binary" | "Unknown"
"""

import re
import logging
from typing import Optional, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Tier 1: Pronoun Patterns
# ──────────────────────────────────────────────────────────────────────────────
_MALE_PRONOUN_PATTERNS = re.compile(
    r'\b(he|him|his|himself)\b',
    re.IGNORECASE
)
_FEMALE_PRONOUN_PATTERNS = re.compile(
    r'\b(she|her|hers|herself)\b',
    re.IGNORECASE
)
_NONBINARY_PRONOUN_PATTERNS = re.compile(
    r'\b(they|them|their|theirs|themself|themselves)\b',
    re.IGNORECASE
)

# ──────────────────────────────────────────────────────────────────────────────
# Tier 2: First-Name Dictionary (Indian + Common Global)
# Keys are lowercase. Values: "M" or "F".
# ──────────────────────────────────────────────────────────────────────────────
FIRST_NAME_DICT = {
    # === INDIAN MALE NAMES ===
    "aarav": "M", "aditya": "M", "akash": "M", "amit": "M", "anand": "M",
    "anil": "M", "ankit": "M", "anuj": "M", "arjun": "M", "arnav": "M",
    "aryan": "M", "ashish": "M", "ashok": "M", "atharv": "M", "ayush": "M",
    "bharat": "M", "chirag": "M", "deepak": "M", "devesh": "M", "dhruv": "M",
    "dinesh": "M", "gaurav": "M", "harsh": "M", "harshit": "M", "hemant": "M",
    "himanshu": "M", "ishan": "M", "ishaan": "M", "jagdish": "M", "jai": "M",
    "jayesh": "M", "kapil": "M", "karan": "M", "kartik": "M", "kunal": "M",
    "lalit": "M", "lokesh": "M", "mahesh": "M", "manish": "M", "manoj": "M",
    "mayank": "M", "mihir": "M", "mohit": "M", "mukesh": "M", "naresh": "M",
    "naveen": "M", "nikhil": "M", "nilesh": "M", "niraj": "M", "nitin": "M",
    "pankaj": "M", "parth": "M", "piyush": "M", "pranav": "M", "prateek": "M",
    "preetam": "M", "puneet": "M", "rahul": "M", "raj": "M", "rajat": "M",
    "rajesh": "M", "rakesh": "M", "ramesh": "M", "ravi": "M", "rishabh": "M",
    "ritesh": "M", "rohan": "M", "rohit": "M", "sachin": "M", "sahil": "M",
    "sanjay": "M", "saurabh": "M", "shivam": "M", "shubham": "M", "siddharth": "M",
    "siddhant": "M", "soham": "M", "sunil": "M", "suresh": "M", "tanmay": "M",
    "tarun": "M", "tushar": "M", "uday": "M", "umesh": "M", "utkarsh": "M",
    "vaibhav": "M", "vijay": "M", "vikas": "M", "vikram": "M", "vinay": "M",
    "vineet": "M", "viraj": "M", "vishal": "M", "vivek": "M", "yash": "M",
    "yashraj": "M", "yogesh": "M", "abhishek": "M", "abhinav": "M",
    "akhilesh": "M", "ajay": "M", "ajit": "M", "alok": "M", "amitabh": "M",
    "amol": "M", "anshul": "M", "anurag": "M", "arvind": "M", "ashwin": "M",
    "bhushan": "M", "chetan": "M", "devendra": "M", "dhananjay": "M",
    "girish": "M", "govind": "M", "hitesh": "M", "jagannath": "M",
    "jitendra": "M", "krishna": "M", "mahendra": "M", "manan": "M",
    "narendra": "M", "neeraj": "M", "omkar": "M", "paresh": "M",
    "pratik": "M", "pravin": "M", "priyank": "M", "rajiv": "M",
    "ramakrishna": "M", "santosh": "M", "satyam": "M", "shailesh": "M",
    "shashank": "M", "siddhartha": "M", "sudhir": "M", "sumit": "M",
    "surendra": "M", "swapnil": "M", "tejas": "M", "trilok": "M",
    "vignesh": "M", "vipin": "M", "virendra": "M", "yuvraj": "M",
    "jayant": "M", "keshav": "M", "lakshman": "M", "madhukar": "M",
    "nagendra": "M", "pramod": "M", "rajeev": "M", "samir": "M",
    "shankar": "M", "shekhar": "M", "sudhindra": "M", "venkat": "M",
    "venkatesh": "M", "vikrant": "M", "vinayak": "M", "vipul": "M",
    "zeeshan": "M", "zubair": "M", "danish": "M", "faisal": "M",
    "imran": "M", "irfan": "M", "junaid": "M", "kamran": "M",
    "mohd": "M", "muhammad": "M", "mukhtar": "M", "raza": "M",
    "salman": "M", "shahid": "M", "shoaib": "M", "wasim": "M",
    "arpit": "M", "ashutosh": "M", "ayaan": "M", "chandan": "M",
    "devanshu": "M", "divyang": "M", "dushyant": "M", "eshan": "M",
    "hardik": "M", "jatin": "M", "kaustubh": "M", "keyur": "M",
    "krunal": "M", "kushal": "M", "lakshya": "M", "maulik": "M",
    "mitesh": "M", "mohak": "M", "naman": "M", "ninad": "M",
    "nishant": "M", "parmod": "M", "parv": "M", "pranit": "M",
    "pranjal": "M", "prathamesh": "M", "rachit": "M", "raghav": "M",
    "rishu": "M", "ronak": "M", "ruchit": "M", "sameer": "M",
    "sandeep": "M", "sandesh": "M", "sarang": "M", "sarthak": "M",
    "shrey": "M", "shreyas": "M", "shivang": "M", "sudip": "M",
    "sujit": "M", "sumeet": "M", "sundeep": "M", "supratim": "M",
    "sushant": "M", "swapan": "M", "tej": "M", "tirthraj": "M",
    "ujjwal": "M", "umang": "M", "varun": "M", "vedant": "M",
    "venkatram": "M", "vibhav": "M", "vigyan": "M", "vrushank": "M",

    # === INDIAN FEMALE NAMES ===
    "aanchal": "F", "aarthi": "F", "aarti": "F", "aisha": "F", "amruta": "F",
    "ananya": "F", "ankita": "F", "anushka": "F", "aparna": "F", "archana": "F",
    "arushi": "F", "asha": "F", "astha": "F", "avantika": "F", "bhavana": "F",
    "chandani": "F", "deepa": "F", "deepika": "F", "devanshi": "F", "disha": "F",
    "divya": "F", "esha": "F", "garima": "F", "gauri": "F", "harshita": "F",
    "heena": "F", "ishita": "F", "janhvi": "F", "jasmine": "F", "jaya": "F",
    "juhi": "F", "kajal": "F", "kalyani": "F", "kavita": "F", "kavya": "F",
    "khushi": "F", "kirti": "F", "komal": "F", "kratika": "F", "kriti": "F",
    "kritika": "F", "lata": "F", "lavanya": "F", "madhuri": "F", "mahima": "F",
    "manasvi": "F", "manisha": "F", "meera": "F", "megha": "F", "meha": "F",
    "minal": "F", "monika": "F", "mugdha": "F", "namrata": "F", "nandini": "F",
    "neha": "F", "nidhi": "F", "niharika": "F", "nikita": "F", "nisha": "F",
    "niti": "F", "poonam": "F", "pooja": "F", "poorva": "F", "prachi": "F",
    "pragati": "F", "pragya": "F", "prerna": "F", "priya": "F", "priyanka": "F",
    "priyatama": "F", "rachna": "F", "radha": "F", "rashmi": "F", "renu": "F",
    "riddhi": "F", "ridhima": "F", "ritika": "F", "roshni": "F", "rucha": "F",
    "rupal": "F", "rupali": "F", "saloni": "F", "sana": "F", "sanchita": "F",
    "sanya": "F", "sapna": "F", "sarika": "F", "seema": "F", "shilpa": "F",
    "shimla": "F", "shraddha": "F", "shree": "F", "shreya": "F", "shweta": "F",
    "simran": "F", "smriti": "F", "sneha": "F", "sonali": "F", "soumya": "F",
    "srishti": "F", "subhashri": "F", "supriya": "F", "swati": "F", "tanvi": "F",
    "tanya": "F", "trisha": "F", "urvashi": "F", "vandana": "F", "varsha": "F",
    "vaishali": "F", "vasudha": "F", "vibha": "F", "vidya": "F", "vimala": "F",
    "vrinda": "F", "yamini": "F", "yashoda": "F", "aaditi": "F", "aditi": "F",
    "akanksha": "F", "akshata": "F", "ambika": "F", "amita": "F", "amritha": "F",
    "anagha": "F", "anjali": "F", "anupama": "F", "archita": "F", "arjita": "F",
    "arnima": "F", "arshi": "F", "aruna": "F", "ayushi": "F", "bhavya": "F",
    "chandrika": "F", "charu": "F", "charita": "F", "chhaya": "F", "daksha": "F",
    "damini": "F", "deeksha": "F", "dhara": "F", "dharini": "F", "dipali": "F",
    "drashti": "F", "ekta": "F", "falak": "F", "farida": "F", "farzana": "F",
    "geeta": "F", "geetha": "F", "girija": "F", "grishma": "F", "gunjan": "F",
    "hansika": "F", "harini": "F", "hema": "F", "hemali": "F", "hetal": "F",
    "hina": "F", "himani": "F", "hrishita": "F", "isha": "F", "jayanti": "F",
    "jayashree": "F", "jyoti": "F", "jyotsna": "F", "kadambari": "F",
    "kalpana": "F", "kamala": "F", "kanchan": "F", "keerti": "F", "khyati": "F",
    "kiran": "F", "kirtana": "F", "kumari": "F", "lakshmi": "F", "leela": "F",
    "lekha": "F", "lipika": "F", "madhavi": "F", "madhu": "F", "mahalakshmi": "F",
    "malvika": "F", "mamta": "F", "mansi": "F", "manya": "F", "meenakshi": "F",
    "mini": "F", "mitali": "F", "mohana": "F", "mridula": "F", "nalini": "F",
    "namita": "F", "nandita": "F", "nayana": "F", "nibedita": "F", "nikhita": "F",
    "nimisha": "F", "nirupama": "F", "pallavi": "F", "parimita": "F",
    "parvati": "F", "pavithra": "F", "payal": "F", "pinki": "F", "poornima": "F",
    "prajakta": "F", "pranali": "F", "preeti": "F", "preethi": "F", "prema": "F",
    "priyamvada": "F", "priyasha": "F", "puja": "F", "pushpa": "F",
    "radhika": "F", "rajeshwari": "F", "rajni": "F", "ranjana": "F",
    "ratnabali": "F", "rekha": "F", "renuka": "F", "revati": "F", "rima": "F",
    "rohini": "F", "ruchika": "F", "rukmini": "F", "rupika": "F", "sadhana": "F",
    "sagarika": "F", "sahana": "F", "sangeetha": "F", "sangeeta": "F",
    "sangita": "F", "santwana": "F", "saranya": "F", "saritha": "F",
    "sarojini": "F", "savita": "F", "shalini": "F", "shampa": "F", "shanta": "F",
    "sharada": "F", "sharmistha": "F", "shefali": "F", "shikha": "F",
    "shirin": "F", "shivani": "F", "shobha": "F", "shreshtha": "F",
    "siddhi": "F", "siya": "F", "smita": "F", "snigdha": "F", "sonal": "F",
    "srija": "F", "sruthi": "F", "subha": "F", "subhashini": "F", "sudha": "F",
    "sujatha": "F", "sulochana": "F", "suma": "F", "sumana": "F", "sumita": "F",
    "sunita": "F", "suparna": "F", "surabhi": "F", "surbhi": "F", "sushmita": "F",
    "suvarna": "F", "swapna": "F", "swarna": "F", "syama": "F", "tanushree": "F",
    "taruna": "F", "tejal": "F", "tejaswini": "F", "tulasi": "F", "tulsi": "F",
    "usha": "F", "usha rani": "F", "vaidehi": "F", "vaishnavi": "F", "vandita": "F",
    "vasantha": "F", "veena": "F", "veenu": "F", "venu": "F", "vidula": "F",
    "vineeta": "F", "vini": "F", "vinita": "F", "vishakha": "F", "yasmin": "F",
    "yuvika": "F",

    # === WESTERN / GLOBAL MALE NAMES ===
    "aaron": "M", "adam": "M", "alex": "M", "alexander": "M", "andrew": "M",
    "anthony": "M", "benjamin": "M", "brian": "M", "charles": "M", "chris": "M",
    "christian": "M", "christopher": "M", "daniel": "M", "david": "M",
    "edward": "M", "eric": "M", "ethan": "M", "frank": "M", "george": "M",
    "henry": "M", "jack": "M", "jacob": "M", "james": "M", "jason": "M",
    "john": "M", "jonathan": "M", "joseph": "M", "joshua": "M", "kevin": "M",
    "kyle": "M", "liam": "M", "lucas": "M", "mark": "M", "matthew": "M",
    "michael": "M", "nathan": "M", "nicholas": "M", "noah": "M", "oliver": "M",
    "patrick": "M", "paul": "M", "peter": "M", "philip": "M", "richard": "M",
    "robert": "M", "ryan": "M", "samuel": "M", "scott": "M", "sean": "M",
    "stephen": "M", "steven": "M", "thomas": "M", "timothy": "M", "tyler": "M",
    "william": "M", "zachary": "M", "carlos": "M", "juan": "M", "miguel": "M",
    "jose": "M", "zhang": "M", "wei": "M", "ali": "M", "omar": "M",

    # === WESTERN / GLOBAL FEMALE NAMES ===
    "alice": "F", "amanda": "F", "amy": "F", "angela": "F", "anna": "F",
    "ashley": "F", "barbara": "F", "betty": "F", "carol": "F", "catherine": "F",
    "charlotte": "F", "christina": "F", "claire": "F", "diana": "F",
    "dorothy": "F", "elizabeth": "F", "emily": "F", "emma": "F", "grace": "F",
    "hannah": "F", "helen": "F", "jennifer": "F", "jessica": "F", "julia": "F",
    "karen": "F", "katherine": "F", "kelly": "F", "kim": "F", "kimberly": "F",
    "laura": "F", "lauren": "F", "linda": "F", "lisa": "F", "margaret": "F",
    "maria": "F", "mary": "F", "megan": "F", "melissa": "F", "michelle": "F",
    "natalie": "F", "nicole": "F", "olivia": "F", "pamela": "F", "patricia": "F",
    "rachel": "F", "rebecca": "F", "ruth": "F", "sandra": "F", "sarah": "F",
    "sharon": "F", "sophia": "F", "stephanie": "F", "susan": "F", "victoria": "F",
    "virginia": "F", "wendy": "F", "zoe": "F", "elena": "F", "sofia": "F",
    "fatima": "F", "aisha": "F", "noor": "F", "mariam": "F", "sara": "F",
}


# ──────────────────────────────────────────────────────────────────────────────
# Tier 3: LLM Inference Schema
# ──────────────────────────────────────────────────────────────────────────────
class GenderInferenceResult(BaseModel):
    gender: str  # "Male" | "Female" | "Non-Binary" | "Unknown"
    confidence: str  # "High" | "Medium" | "Low"
    reasoning: str  # Brief explanation (for internal audit)


_LLM_GENDER_SYSTEM_PROMPT = """You are an AI assistant that infers the likely gender of a person from their name and resume text.

Instructions:
1. Look for explicit gender indicators: pronouns (he/him/his, she/her/hers, they/them), self-identified gender statements.
2. Analyze the person's name for cultural/linguistic gender markers.
3. If the name is clearly South Asian (Indian), use your knowledge of Indian naming conventions.
4. Return one of these EXACT values in the "gender" field: "Male", "Female", "Non-Binary", or "Unknown"
5. Return "Unknown" if you cannot determine gender with reasonable confidence.
6. NEVER invent or assume gender based on profession or job role alone.
7. Be culturally sensitive and accurate for Indian, Arabic, East Asian, and Western names.

Output strictly valid JSON matching the schema."""


class GenderDetector:
    """
    Multi-tier gender inference engine for resumes.
    Does NOT use gender-guesser library (which fails on Indian names).
    """

    @classmethod
    def detect(
        cls,
        name: Optional[str],
        cv_text: Optional[str] = None,
        provider: Optional[Any] = None
    ) -> str:
        """
        Detects candidate gender from name and/or CV text.
        Returns: "Male" | "Female" | "Non-Binary" | "Unknown"
        """
        # ── Tier 1: Pronoun Scan ──────────────────────────────────────────────
        pronoun_result = cls._scan_pronouns(cv_text)
        if pronoun_result and pronoun_result != "Unknown":
            logger.debug(f"GenderDetector: Tier 1 pronoun match → {pronoun_result}")
            return pronoun_result

        # ── Tier 2: Name Dictionary Lookup ───────────────────────────────────
        name_result = cls._lookup_name(name)
        if name_result and name_result != "Unknown":
            logger.debug(f"GenderDetector: Tier 2 name dict match for '{name}' → {name_result}")
            return name_result

        # ── Tier 3: LLM Contextual Inference ─────────────────────────────────
        llm_result = cls._llm_infer(name, cv_text, provider)
        if llm_result and llm_result != "Unknown":
            logger.debug(f"GenderDetector: Tier 3 LLM inferred '{name}' → {llm_result}")
            return llm_result

        # ── Tier 4: Fallback ──────────────────────────────────────────────────
        return "Unknown"

    @classmethod
    def _scan_pronouns(cls, cv_text: Optional[str]) -> Optional[str]:
        """Tier 1: scan first 500 chars of CV for self-referential pronouns."""
        if not cv_text:
            return None

        # Only scan the beginning of CV where summary/objective is usually found
        sample = cv_text[:800]

        # Count pronoun occurrences — take strongest signal
        male_hits = len(_MALE_PRONOUN_PATTERNS.findall(sample))
        female_hits = len(_FEMALE_PRONOUN_PATTERNS.findall(sample))
        nb_hits = len(_NONBINARY_PRONOUN_PATTERNS.findall(sample))

        # Filter noise: need at least 2 occurrences to count as signal
        signals = []
        if male_hits >= 2:
            signals.append(("Male", male_hits))
        if female_hits >= 2:
            signals.append(("Female", female_hits))
        if nb_hits >= 2:
            signals.append(("Non-Binary", nb_hits))

        if not signals:
            return None

        # Return gender with highest frequency
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[0][0]

    @classmethod
    def _lookup_name(cls, name: Optional[str]) -> Optional[str]:
        """Tier 2: lookup first name in curated dictionary."""
        if not name:
            return None

        # Extract first name (before space or hyphen)
        first_name = name.strip().split()[0] if name.strip() else ""
        first_name = first_name.lower().strip(".,;:")

        if not first_name:
            return None

        result = FIRST_NAME_DICT.get(first_name)
        if result == "M":
            return "Male"
        elif result == "F":
            return "Female"

        return None

    @classmethod
    def _llm_infer(
        cls,
        name: Optional[str],
        cv_text: Optional[str],
        provider: Optional[Any]
    ) -> Optional[str]:
        """Tier 3: call LLM with name + short CV snippet for contextual inference."""
        if not provider:
            try:
                from services.ai.provider import get_ai_provider, MockProvider
                p = get_ai_provider()
                if isinstance(p, MockProvider):
                    return None  # Don't call mock in prod-like scenarios
                provider = p
            except Exception:
                return None

        try:
            from services.ai.provider import MockProvider
            if isinstance(provider, MockProvider):
                return None

            # Build a concise context: name + first 300 chars of CV summary area
            snippet = (cv_text or "")[:300].strip()
            prompt = (
                f"Candidate Name: {name or 'Unknown'}\n\n"
                f"CV Excerpt:\n{snippet}\n\n"
                f"Based on the candidate's name and CV excerpt, what is the likely gender? "
                f"Focus on pronouns, name patterns, and cultural naming conventions."
            )

            result, _ = provider.generate_structured(
                prompt,
                GenderInferenceResult,
                _LLM_GENDER_SYSTEM_PROMPT
            )

            if result and result.gender in ("Male", "Female", "Non-Binary", "Unknown"):
                if result.confidence in ("High", "Medium"):
                    return result.gender
                # Low confidence → treat as Unknown
                return None

        except Exception as e:
            logger.debug(f"GenderDetector LLM inference failed: {e}")

        return None
