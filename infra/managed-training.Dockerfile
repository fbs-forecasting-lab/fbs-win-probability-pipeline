# Candidate only: supply an approved immutable Linux x86_64 base digest.
ARG TRAINING_BASE_IMAGE
FROM ${TRAINING_BASE_IMAGE}
WORKDIR /var/task
# Build context contains only the reviewed Linux package and this new entrypoint.
COPY cloud-stakeholder.zip /tmp/application.zip
RUN /var/lang/bin/python3.14 -c "import zipfile; zipfile.ZipFile('/tmp/application.zip').extractall('/var/task')"
COPY managed_training.py /var/task/src/pipeline/managed_training.py
ENV PYTHONPATH=/var/task
ENTRYPOINT ["/var/lang/bin/python3.14", "-B", "-m", "src.pipeline.managed_training"]
