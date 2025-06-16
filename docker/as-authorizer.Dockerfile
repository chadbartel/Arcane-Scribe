#----------------------------------------------------------------
# Stage 1: The "builder" stage
# This stage's only job is to install Python dependencies into a clean directory.
#----------------------------------------------------------------
FROM public.ecr.aws/lambda/python:3.12 AS builder

# Copy only the requirements file for the specific Lambda function
COPY src/as-authorizer/requirements.txt ./

# Install dependencies into a target directory that we will copy later.
# Using /opt/python is a good practice as it mimics the layer structure.
RUN pip install -r requirements.txt --target /opt/python

#----------------------------------------------------------------
# Stage 2: The final production image
# This stage builds the lean, final image to be deployed.
#----------------------------------------------------------------
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory inside the Lambda environment
ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the pre-installed dependencies from the 'builder' stage.
COPY --from=builder /opt/python ${LAMBDA_TASK_ROOT}

# Copy the shared core module. The path is relative to the build context (project root).
COPY src/core/ ${LAMBDA_TASK_ROOT}/core/

# Copy the application-specific code for the API backend.
COPY src/as-authorizer/ ${LAMBDA_TASK_ROOT}/

# Set the command to your handler file and function.
CMD [ "handler.lambda_handler" ]