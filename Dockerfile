# Start from Python 3.11 base image
FROM public.ecr.aws/docker/library/python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file and the application files to the working directory
COPY requirements.txt app.py utils.py forecast_model.py ./

# Install any dependencies
RUN pip install --no-cache -r requirements.txt

# Copy the content of the local .streamlit directory to the container
COPY .streamlit/ .streamlit/

# Expose the port the app runs on
EXPOSE 8888

# Command to run the app
CMD ["streamlit", "run", "app.py", "--server.port=8888"]

