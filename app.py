import logging

import pathway as pw
from dotenv import load_dotenv
from pathway.xpacks.llm.question_answering import AdaptiveRAGQuestionAnswerer
from pathway.xpacks.llm.servers import QASummaryRestServer
from pydantic import BaseModel, ConfigDict, InstanceOf
import threading
import uvicorn

# To use advanced features with Pathway Scale, get your free license key from
# https://pathway.com/features and paste it below.
# To use Pathway Community, comment out the line below.
pw.set_license_key("demo-license-key-with-telemetry")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()


class App(BaseModel):
    question_answerer: InstanceOf[AdaptiveRAGQuestionAnswerer]
    host: str = "0.0.0.0"
    port: int = 8000

    with_cache: bool = True
    terminate_on_error: bool = False

    def run(self) -> None:
        server = QASummaryRestServer(self.host, self.port, self.question_answerer)
        server.run(
            with_cache=self.with_cache,
            terminate_on_error=self.terminate_on_error,
            cache_backend=pw.persistence.Backend.filesystem("Cache"),
        )

    model_config = ConfigDict(extra="forbid")


if __name__ == "__main__":
    with open("app.yaml") as f:
        config = pw.load_yaml(f)
    # Start the upload API on port 8001 in a background daemon thread
    def run_uploader():
        uvicorn.run("upload_api:app", host="0.0.0.0", port=8001, log_level="info")

    t = threading.Thread(target=run_uploader, daemon=True)
    t.start()

    app = App(**config)
    app.run()