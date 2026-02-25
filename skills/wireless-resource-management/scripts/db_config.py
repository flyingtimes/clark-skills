#!/usr/bin/env python3
"""
Database configuration for wireless resource management.
Use environment variables for sensitive information.
"""

import os
from dataclasses import dataclass

@dataclass
class DBConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "wireless_db"
    username: str = "postgres"
    password: str = ""
    schema: str = "public"
    
    @classmethod
    def from_env(cls):
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "wireless_db"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            schema=os.getenv("DB_SCHEMA", "public")
        )
    
    def connection_string(self):
        """Return PostgreSQL connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def psycopg2_params(self):
        """Return parameters for psycopg2.connect()."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.username,
            "password": self.password
        }

# Default configuration
config = DBConfig.from_env()

if __name__ == "__main__":
    # Test configuration
    print("Database configuration:")
    print(f"  Host: {config.host}")
    print(f"  Port: {config.port}")
    print(f"  Database: {config.database}")
    print(f"  Username: {config.username}")
    print(f"  Schema: {config.schema}")
    print(f"  Password set: {'Yes' if config.password else 'No'}")