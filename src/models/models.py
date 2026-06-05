from pydantic import BaseModel

class Command(BaseModel):
    command: str

class ReadLine(BaseModel):
    startline:int