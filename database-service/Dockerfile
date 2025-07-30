FROM postgres:15-alpine

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/

# Set environment variables
ENV POSTGRES_DB=music_store
ENV POSTGRES_USER=music_user
ENV POSTGRES_PASSWORD=music_password

# Expose port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD pg_isready -U music_user -d music_store 