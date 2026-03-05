"""
Configuration for the daily arxiv research paper digest.

Defines research interests, keyword profiles, venue patterns,
Zotero settings, and pipeline parameters.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATE_DIR = BASE_DIR / "state"
OUTPUT_DIR = BASE_DIR / "output"
STATE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

PROCESSED_IDS_FILE = STATE_DIR / "processed_ids.json"

# ---------------------------------------------------------------------------
# arxiv RSS
# ---------------------------------------------------------------------------
RSS_CHANNELS = ["cs.RO", "cs.CV", "cs.AI", "cs.LG"]
RSS_FEED_URL = "https://rss.arxiv.org/rss/" + "+".join(RSS_CHANNELS)

# ---------------------------------------------------------------------------
# arxiv API
# ---------------------------------------------------------------------------
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_API_BATCH_SIZE = 50  # IDs per request
ARXIV_API_DELAY = 3.0  # seconds between requests (rate limit)

# ---------------------------------------------------------------------------
# Zotero
# ---------------------------------------------------------------------------
ZOTERO_USER_ID = os.environ.get("ZOTERO_USER_ID", "11347333")
ZOTERO_API_KEY = os.environ.get("ZOTERO_API_KEY", "")
ZOTERO_COLLECTION_KEY = "4YQXTXFL"  # "automated" collection
ZOTERO_API_BASE = f"https://api.zotero.org/users/{ZOTERO_USER_ID}"
ZOTERO_TAG = "arxiv-digest"

# ---------------------------------------------------------------------------
# Research Interest Profiles
# ---------------------------------------------------------------------------
# Each interest is a dict with:
#   - "name": display name
#   - "description": one-line description
#   - "keywords": list of (phrase, weight) tuples
#     Weight reflects how strongly the keyword signals relevance.
#     Higher weight = stronger signal.

INTEREST_PROFILES = [
    {
        "name": "Task Planning & Execution with Atomic Capabilities",
        "description": (
            "Algorithms that schedule, plan, and execute atomic (simple or expert) "
            "actions from natural-language commands to achieve high accuracy and efficiency."
        ),
        "keywords": [
            # Core concepts — high weight
            ("task planning", 3.0),
            ("action planning", 3.0),
            ("task and motion planning", 3.5),
            ("atomic action", 3.5),
            ("action primitive", 3.5),
            ("primitive skill", 3.0),
            ("skill primitive", 3.0),
            ("skill composition", 3.0),
            ("skill chaining", 3.0),
            ("action scheduling", 3.0),
            ("task scheduling", 2.5),
            ("task decomposition", 3.0),
            ("subtask", 2.0),
            ("sub-task", 2.0),
            ("hierarchical planning", 3.0),
            ("hierarchical task", 2.5),
            ("language-conditioned", 2.5),
            ("language conditioned", 2.5),
            ("natural language command", 3.0),
            ("natural language instruction", 3.0),
            ("instruction following", 2.5),
            ("language grounding", 2.5),
            ("grounded language", 2.5),
            # LLM / VLM planning
            ("llm planning", 3.0),
            ("llm-based planning", 3.0),
            ("vlm planning", 3.0),
            ("language model planning", 3.0),
            ("foundation model planning", 2.5),
            ("code as policy", 3.0),
            ("code generation for robot", 2.5),
            # Sequential / compositional
            ("sequential decision", 2.0),
            ("compositional action", 2.5),
            ("compositional task", 2.5),
            ("long-horizon", 2.5),
            ("long horizon", 2.5),
            ("multi-step task", 2.5),
            ("multi-step manipulation", 2.5),
            # Broader but still relevant
            ("chain of thought", 1.5),
            ("chain-of-thought", 1.5),
            ("tool use", 1.5),
            ("affordance", 1.5),
            ("semantic planning", 2.0),
            ("symbolic planning", 2.0),
            ("pddl", 2.5),
            ("behavior tree", 2.0),
            ("state machine", 1.5),
            ("finite state", 1.0),
            ("robot plan", 2.0),
            ("plan execution", 2.5),
            ("motion planning", 1.0),
            ("manipulation planning", 2.0),
            ("pick and place", 1.0),
            ("open-vocabulary", 1.5),
            ("zero-shot task", 2.0),
        ],
    },
    {
        "name": "Edge / Efficient Inference for Robot Learning",
        "description": (
            "Proposals to enable fast, real-time inference of robot learning algorithms "
            "(planning or action policy) on edge platforms, via platform-based optimization "
            "or efficient network design."
        ),
        "keywords": [
            # Core concepts — high weight
            ("edge deployment", 3.5),
            ("edge device", 3.0),
            ("edge inference", 3.5),
            ("on-device", 3.0),
            ("on device inference", 3.5),
            ("embedded system", 2.0),
            ("embedded platform", 2.5),
            ("jetson", 3.0),
            ("nvidia jetson", 3.5),
            ("raspberry pi", 2.0),
            # Model compression & optimization
            ("model compression", 3.0),
            ("quantization", 2.5),
            ("quantized", 2.0),
            ("pruning", 2.0),
            ("knowledge distillation", 2.5),
            ("distillation", 1.5),
            ("weight sharing", 2.0),
            ("neural architecture search", 2.5),
            ("efficient neural", 2.0),
            ("efficient network", 2.0),
            ("efficient model", 2.0),
            ("lightweight model", 2.5),
            ("lightweight network", 2.5),
            ("compact model", 2.0),
            ("small model", 1.0),
            ("model efficiency", 2.5),
            # Inference optimization
            ("inference optimization", 3.0),
            ("inference speed", 2.5),
            ("inference latency", 3.0),
            ("inference time", 2.0),
            ("fast inference", 3.0),
            ("real-time inference", 3.5),
            ("real time inference", 3.5),
            ("low-latency", 2.5),
            ("low latency", 2.5),
            ("latency reduction", 2.5),
            ("runtime optimization", 2.5),
            # Frameworks
            ("tensorrt", 3.0),
            ("onnx runtime", 2.5),
            ("tflite", 2.5),
            ("openvino", 2.5),
            ("llama.cpp", 2.5),
            ("gguf", 2.5),
            # Robot-specific efficiency
            ("real-time control", 2.0),
            ("real-time policy", 3.0),
            ("efficient policy", 2.5),
            ("efficient robot", 2.5),
            ("efficient manipulation", 2.0),
            ("fast policy", 2.5),
            ("control frequency", 2.0),
            ("compute budget", 2.0),
            ("resource-constrained", 2.5),
            ("resource constrained", 2.5),
            ("compute-efficient", 2.5),
            ("compute efficient", 2.5),
            ("hardware-aware", 2.5),
            ("hardware aware", 2.5),
            ("deploying", 1.0),
            ("deployment", 1.0),
        ],
    },
]

# ---------------------------------------------------------------------------
# Relevance Scoring
# ---------------------------------------------------------------------------
# A paper is relevant if its combined score exceeds this threshold.
# Tuned for balanced precision/recall on ~700 daily papers → ~30-80 matches.
RELEVANCE_THRESHOLD = 4.0

# Bonus for papers whose primary category is in our channels
CATEGORY_BONUS = {"cs.RO": 0.5, "cs.CV": 0.0, "cs.AI": 0.2, "cs.LG": 0.0}

# Title keyword matches get this multiplier
TITLE_MULTIPLIER = 2.0

# Max results per day (user requested cap of 200)
MAX_RESULTS = 200

# ---------------------------------------------------------------------------
# Venue Patterns
# ---------------------------------------------------------------------------
# Maps venue abbreviation → (full name, type)
# type: "conference" or "journal"
VENUE_PATTERNS = {
    # Robotics conferences
    "ICRA": ("IEEE International Conference on Robotics and Automation", "conference"),
    "IROS": ("IEEE/RSJ International Conference on Intelligent Robots and Systems", "conference"),
    "CoRL": ("Conference on Robot Learning", "conference"),
    "RSS": ("Robotics: Science and Systems", "conference"),
    "HRI": ("ACM/IEEE International Conference on Human-Robot Interaction", "conference"),
    "ISRR": ("International Symposium of Robotics Research", "conference"),
    "CASE": ("IEEE International Conference on Automation Science and Engineering", "conference"),
    "Humanoids": ("IEEE-RAS International Conference on Humanoid Robots", "conference"),
    "RoboSoft": ("IEEE International Conference on Soft Robotics", "conference"),
    # Computer vision conferences
    "CVPR": ("IEEE/CVF Conference on Computer Vision and Pattern Recognition", "conference"),
    "ICCV": ("IEEE/CVF International Conference on Computer Vision", "conference"),
    "ECCV": ("European Conference on Computer Vision", "conference"),
    "WACV": ("IEEE/CVF Winter Conference on Applications of Computer Vision", "conference"),
    "BMVC": ("British Machine Vision Conference", "conference"),
    "ACCV": ("Asian Conference on Computer Vision", "conference"),
    "3DV": ("International Conference on 3D Vision", "conference"),
    # Machine learning conferences
    "NeurIPS": ("Neural Information Processing Systems", "conference"),
    "NIPS": ("Neural Information Processing Systems", "conference"),
    "ICML": ("International Conference on Machine Learning", "conference"),
    "ICLR": ("International Conference on Learning Representations", "conference"),
    "AISTATS": ("International Conference on Artificial Intelligence and Statistics", "conference"),
    "COLT": ("Conference on Learning Theory", "conference"),
    "UAI": ("Conference on Uncertainty in Artificial Intelligence", "conference"),
    "AutoML": ("International Conference on Automated Machine Learning", "conference"),
    # AI conferences
    "AAAI": ("AAAI Conference on Artificial Intelligence", "conference"),
    "IJCAI": ("International Joint Conference on Artificial Intelligence", "conference"),
    "ECAI": ("European Conference on Artificial Intelligence", "conference"),
    # NLP conferences (occasionally relevant)
    "ACL": ("Annual Meeting of the Association for Computational Linguistics", "conference"),
    "EMNLP": ("Conference on Empirical Methods in Natural Language Processing", "conference"),
    "NAACL": ("North American Chapter of the Association for Computational Linguistics", "conference"),
    # Other relevant
    "SIGGRAPH": ("ACM SIGGRAPH", "conference"),
    "IV": ("IEEE Intelligent Vehicles Symposium", "conference"),
    "ITSC": ("IEEE International Conference on Intelligent Transportation Systems", "conference"),
    # Journals
    "RA-L": ("IEEE Robotics and Automation Letters", "journal"),
    "RAL": ("IEEE Robotics and Automation Letters", "journal"),
    "T-RO": ("IEEE Transactions on Robotics", "journal"),
    "TRO": ("IEEE Transactions on Robotics", "journal"),
    "IJRR": ("The International Journal of Robotics Research", "journal"),
    "RAS": ("Robotics and Autonomous Systems", "journal"),
    "JFR": ("Journal of Field Robotics", "journal"),
    "AuRo": ("Autonomous Robots", "journal"),
    "T-PAMI": ("IEEE Transactions on Pattern Analysis and Machine Intelligence", "journal"),
    "TPAMI": ("IEEE Transactions on Pattern Analysis and Machine Intelligence", "journal"),
    "IJCV": ("International Journal of Computer Vision", "journal"),
    "JMLR": ("Journal of Machine Learning Research", "journal"),
    "Nature": ("Nature", "journal"),
    "Science": ("Science", "journal"),
    "Science Robotics": ("Science Robotics", "journal"),
}

# Longer venue name aliases that should be checked first (before short ones)
# to avoid false matches (e.g., "RSS" matching random text).
VENUE_LONG_NAMES = {
    "Robotics: Science and Systems": ("RSS", "conference"),
    "Robotics and Automation Letters": ("RA-L", "journal"),
    "Transactions on Robotics": ("T-RO", "journal"),
    "Science Robotics": ("Science Robotics", "journal"),
    "Intelligent Vehicles Symposium": ("IV", "conference"),
}

# Short venue names that are risky for false positives — require context
VENUE_CONTEXT_REQUIRED = {"RSS", "IV", "ACL"}
