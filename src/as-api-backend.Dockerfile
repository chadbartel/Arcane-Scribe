# Builder image
FROM public.ecr.aws/lambda/python:3.12 AS builder

# Copy core module
COPY core/ /var/task/core/

# Use the official AWS Lambda Python base image for Python 3.12
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory
ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the installed dependencies from the 'builder' stage
COPY --from=builder /opt/python ${LAMBDA_TASK_ROOT}

# Copy function code
COPY as-api-backend/handler.py ${LAMBDA_TASK_ROOT}/
ADD as-api-backend/api_backend/ ${LAMBDA_TASK_ROOT}/api_backend

# Install dependencies from requirements.txt
COPY as-api-backend/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "handler.lambda_handler" ]