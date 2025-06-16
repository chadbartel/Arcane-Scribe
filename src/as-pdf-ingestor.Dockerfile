# Builder image
FROM public.ecr.aws/lambda/python:3.12 AS builder

# Copy core module
COPY core/ /var/task/core/

# Use the official AWS Lambda Python base image for Python 3.12
FROM public.ecr.aws/lambda/python:3.12

# Set the root directory for the Lambda function, also the working directory
ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the installed dependencies from the 'builder' stage
COPY --from=builder /opt/python ${LAMBDA_TASK_ROOT}

# Copy function code
COPY as-pdf-ingestor/handler.py ${LAMBDA_TASK_ROOT}/
COPY as-pdf-ingestor/api_authorizer/ ${LAMBDA_TASK_ROOT}/api_authorizer

# Copy requirements.txt first to leverage Docker caching
COPY as-pdf-ingestor/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "handler.lambda_handler" ]