FROM debian:stable

LABEL maintainer="PharmAI GmbH <contact@pharm.ai>" \
        org.label-schema.name="PLIP: The Protein-Ligand Interaction Profiler" \
        org.label-schema.description="https://www.doi.org/10.1093/nar/gkv315"

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    pymol \
    python3-distutils \
    python3-lxml \
    python3-openbabel \
    python3-pymol \
    python3-pip \
    python3-dev; \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for API
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

# copy PLIP source code
WORKDIR /src
COPY . .
RUN chmod +x plip/plipcmd.py
ENV PYTHONPATH=/src

# Create storage directory for results
RUN mkdir -p /storage && chmod 777 /storage

# Switch entry point to API
EXPOSE 8000
CMD ["uvicorn", "plip.plip_api:app", "--host", "0.0.0.0", "--port", "8000"]
