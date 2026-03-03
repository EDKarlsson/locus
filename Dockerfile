FROM python:3.12-slim
RUN pip install --no-cache-dir "locus-mcp==0.6.2"
ENTRYPOINT ["locus-mcp"]
