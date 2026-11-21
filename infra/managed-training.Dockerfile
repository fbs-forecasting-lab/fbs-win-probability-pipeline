# Reviewed Linux x86_64 manifest; never follow a mutable tag at build time.
ARG TRAINING_BASE_IMAGE=public.ecr.aws/lambda/python@sha256:bbe0b5c9f1b049d9b0a77b742cfd252b2c0ccfb153f259df4d830c798dd63dd3
FROM ${TRAINING_BASE_IMAGE}
WORKDIR /var/task
# Build context contains only the reviewed package and the managed adapter source.
COPY cloud-stakeholder.zip /tmp/application.zip
RUN /var/lang/bin/python3.14 -c "import zipfile; zipfile.ZipFile('/tmp/application.zip').extractall('/var/task')"
COPY managed_*.py /var/task/src/pipeline/
ENV PYTHONPATH=/var/task
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["/var/lang/bin/python3.14", "-B", "-m", "src.pipeline.managed_training"]
