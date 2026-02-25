import json
import os
import logging
from config.settings import OUTPUT_DIR

log = logging.getLogger(__name__)
HISTORY_FILE = os.path.join(OUTPUT_DIR, "topic_history.json")

def get_recent_topics(limit=10):
    """Load recently used topics from history file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_topic_to_history(topic):
    """Save a new topic to history."""
    history = get_recent_topics()
    history.insert(0, topic)
    # Keep only last 20
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[:20], f, indent=2)
    log.info(f"Topic saved to history: {topic}")
