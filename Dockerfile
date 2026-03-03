FROM python:3.12-slim
ARG LOCUS_MCP_VERSION="0.6.2"
RUN pip install --no-cache-dir "locus-mcp==${LOCUS_MCP_VERSION}"
ENTRYPOINT ["locus-mcp"]
