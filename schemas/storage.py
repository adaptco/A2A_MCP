import logging

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self):
        self.artifacts = {}

    def save_artifact(self, artifact):
        logger.info(f"Saving artifact: {artifact.artifact_id}")
        self.artifacts[artifact.artifact_id] = artifact