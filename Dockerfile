    # Use an official Python runtime as a parent image                                                           
    FROM python:3.10-slim                                                                                        
                                                                                                                 
    # Set the working directory in the container                                                                 
    WORKDIR /app                                                                                                 
                                                                                                                 
    # Copy the requirements file into the container                                                              
    COPY requirements.txt .                                                                                      
                                                                                                                 
    # Install any dependencies                                                                                   
    RUN pip install --no-cache-dir -r requirements.txt                                                           
                                                                                                                 
    # Copy the rest of the application files into the container                                                  
    COPY . .                                                                                                     
                                                                                                                 
    # Set environment variables                                                                                  
    ENV GEMINI_API_KEY="AIzaSyD4UfHmxR2aQH-YnuCi8ukZ7SGEW26Fjbw"                                                                                        
    ENV SLACK_KEY=""                                                                                             
    ENV SLACK_CHANNEL_ID=""                                                                                      
                                                                                                                 
    # Expose the port the app runs on                                                                            
    EXPOSE 8000                                                                                                  
                                                                                                                 
    # Command to run the application                                                                             
    CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]   