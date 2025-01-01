    # Use an official Python runtime as a parent image                                                           
    FROM python:3.10-slim                                                                                        
                                                                                                                 
    # Install cron                                                                                               
    RUN apt-get update && apt-get install -y cron                                                                 
                                 
    # set datetime 
    # Set timezone to EST
    RUN apt-get install -y tzdata
    ENV TZ=America/New_York
    RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

    # Set the working directory in the container                                                                 
    WORKDIR /app                                                                                                 
                                                                                                                 
    # Copy the requirements file into the container                                                              
    COPY requirements.txt .                                                                                      
                                                                                                                 
    # Install any dependencies                                                                                   
    RUN pip install --no-cache-dir -r requirements.txt                                                           
                                                                                                                 
    # Copy the rest of the application files into the container                                                  
    COPY . .                                                                                                     
                                                                                                                 
    # Create cron job                                                                                            
    RUN echo "0 9 * * * cd /app && python main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/daily-job               
    RUN chmod 0644 /etc/cron.d/daily-job                                                                          
    RUN crontab /etc/cron.d/daily-job                                                                           
                                                                                                                 
    # Create the log file to be able to run tail                                                                 
    RUN touch /var/log/cron.log                                                                                   
                                                                                                                 
    # Create cache directory
    RUN mkdir -p /app/out/cache
    
    # Copy default config files
    COPY configs /app/configs
    
    # Set environment variables                                                                                  
    ENV GEMINI_API_KEY=""                                                                                        
    ENV SLACK_KEY=""                                                                                             
    ENV SLACK_CHANNEL_ID=""                                                                                      
                                                                                                                 
    # Expose the port the app runs on                                                                            
    EXPOSE 8000                                                                                                  
                                                                                                                 
    # Create start script                                                                                       
    RUN echo "#!/bin/bash\npython main.py >> /var/log/cron.log 2>&1\ncron\ngunicorn --bind 0.0.0.0:8000 app:app" > /app/start.sh                           
    RUN chmod +x /app/start.sh                                                                                   
                                                                                                                 
    # Command to run main.py immediately, then start cron and gunicorn                                                                      
    CMD ["/app/start.sh"]   
