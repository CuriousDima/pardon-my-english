# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory to /app
WORKDIR /app

# Copy the directory containing the application into the container at /app
COPY telegram-bot/ /app/
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
# (Not needed since this application does not use a network port, but left for reference)
# EXPOSE 80

# Define environment variables
ENV DB_URI="sqlite:////app/data/pardon-my-english-accounts.db"
ENV TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV GROQ_API_KEY=${GROQ_API_KEY}

# Set up a directory for the SQLite database
VOLUME /app/data

# Make sure the directory for SQLite database exists
RUN mkdir /app/data

# Run bot.py when the container launches
CMD ["python", "bot.py"]