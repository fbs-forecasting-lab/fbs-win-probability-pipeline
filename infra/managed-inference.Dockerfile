# Verify this local tag against the original immutable producer digest before
# building; the recovery manifest also verifies every inherited layer afterward.
# No registry pull, dependency installation or refit is needed.
ARG TRAINING_IMAGE=fbs-managed-training:pm09a-final
FROM ${TRAINING_IMAGE}
COPY managed_archive.py managed_lineage.py managed_inference.py /var/task/src/pipeline/
ENTRYPOINT ["/lambda-entrypoint.sh"]
CMD ["src.pipeline.managed_inference.handler"]
