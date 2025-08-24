# Frontend Developer Agent
# File: agents/frontend_dev/agent.py
import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from nats.aio.client import Client as NATS
import redis
import psycopg
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ComponentSpec:
    framework: str
    component_type: str
    requirements: list
    styling: str = "tailwind"
    accessibility: bool = True

class FrontendDevAgent:
    def __init__(self, agent_id: str = "frontend_dev_001"):
        self.agent_id = agent_id
        self.role = "frontend_dev"
        self.status = "starting"
        self.processed_tasks = 0
        
        # Connections
        self.nats_client: Optional[NATS] = None
        self.redis_client: Optional[redis.Redis] = None
        self.db_connection_uri = os.getenv("POSTGRES_URI", "postgresql://user:pass@db:5432/factory")
        
    async def connect(self):
        """Initialize connections"""
        try:
            # NATS connection
            self.nats_client = NATS()
            nats_url = os.getenv("NATS_URL", "nats://nats:4222")
            await self.nats_client.connect(nats_url, max_reconnect_attempts=5)
            logger.info(f"✅ [{self.agent_id}] Connected to NATS")
            
            # Redis connection
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"✅ [{self.agent_id}] Connected to Redis")
            
            self.status = "ready"
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Connection failed: {e}")
            self.status = "error"
            raise
    
    async def message_handler(self, msg):
        """Handle incoming frontend development tasks"""
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("task_id")
            
            logger.info(f"⚛️ [{self.agent_id}] Received frontend task: {task_id}")
            
            await self.update_task_status(task_id, "processing")
            result = await self.process_task(data)
            await self.update_task_status(task_id, "completed", result=result)
            
            self.processed_tasks += 1
            logger.info(f"✅ [{self.agent_id}] Completed frontend task: {task_id}")
            
        except Exception as e:
            task_id = "unknown"
            try:
                data = json.loads(msg.data.decode())
                task_id = data.get("task_id", "unknown")
            except:
                pass
            
            logger.error(f"❌ [{self.agent_id}] Frontend task {task_id} failed: {e}")
            await self.update_task_status(task_id, "failed", error=str(e))
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process frontend development task"""
        self.status = "working"
        
        try:
            payload = task_data.get("payload", {})
            spec = ComponentSpec(
                framework=payload.get("framework", "react"),
                component_type=payload.get("component_type", "functional"),
                requirements=payload.get("requirements", []),
                styling=payload.get("styling", "tailwind"),
                accessibility=payload.get("accessibility", True)
            )
            
            # Generate component code
            component_code = self.generate_component(spec, payload.get("name", "Component"))
            
            # Generate tests if requested
            tests = ""
            if "testing" in payload.get("requirements", []):
                tests = self.generate_tests(spec, payload.get("name", "Component"))
            
            # Generate styles if needed
            styles = ""
            if spec.styling == "css":
                styles = self.generate_styles(payload.get("name", "Component"))
            
            self.status = "ready"
            return {
                "component": component_code,
                "tests": tests,
                "styles": styles,
                "framework": spec.framework,
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.status = "error"
            raise Exception(f"Frontend development failed: {str(e)}")
    
    def generate_component(self, spec: ComponentSpec, name: str) -> str:
        """Generate component code based on specification"""
        
        if spec.framework.lower() == "react":
            return self.generate_react_component(spec, name)
        elif spec.framework.lower() == "vue":
            return self.generate_vue_component(spec, name)
        elif spec.framework.lower() == "angular":
            return self.generate_angular_component(spec, name)
        else:
            return self.generate_react_component(spec, name)  # Default to React
    
    def generate_react_component(self, spec: ComponentSpec, name: str) -> str:
        """Generate React component"""
        imports = ["import React"]
        
        if "state" in spec.requirements:
            imports.append("import { useState, useEffect }")
        
        if "routing" in spec.requirements:
            imports.append("import { useNavigate, Link }")
        
        if "api" in spec.requirements:
            imports.append("import axios")
        
        component_type = "const" if spec.component_type == "functional" else "class"
        
        if spec.component_type == "functional":
            hooks = []
            if "state" in spec.requirements:
                hooks.append("  const [data, setData] = useState(null);")
                hooks.append("  const [loading, setLoading] = useState(false);")
            
            if "api" in spec.requirements:
                hooks.append("""
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await axios.get('/api/data');
        setData(response.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);""")
            
            hooks_code = "\n".join(hooks) if hooks else ""
            
            accessibility_props = 'role="main" aria-label="Main content"' if spec.accessibility else ''
            
            return f"""// {name} Component - Generated by Multi-Agent Factory
{"; ".join(imports)} from 'react';
{"import './styles.css';" if spec.styling == "css" else ""}

{component_type} {name} = () => {{
{hooks_code}

  return (
    <div className="{"" if spec.styling == "tailwind" else f"{name.lower()}-container"}" {accessibility_props}>
      <header className="{"mb-6" if spec.styling == "tailwind" else "header"}">
        <h1 className="{"text-3xl font-bold text-gray-900" if spec.styling == "tailwind" else "title"}">
          {name}
        </h1>
      </header>
      
      <main className="{"space-y-4" if spec.styling == "tailwind" else "content"}">
        {"<div className=\"flex items-center justify-center p-4\"><div className=\"animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600\"></div></div>" if "state" in spec.requirements else ""}
        {"{loading && <LoadingSpinner />}" if "state" in spec.requirements else ""}
        {"{data && <DataDisplay data={data} />}" if "api" in spec.requirements else ""}
        
        <section className="{"bg-white p-6 rounded-lg shadow-md" if spec.styling == "tailwind" else "section"}">
          <h2 className="{"text-xl font-semibold mb-4" if spec.styling == "tailwind" else "section-title"}">
            Content Section
          </h2>
          <p className="{"text-gray-600" if spec.styling == "tailwind" else "description"}">
            This is a generated {spec.framework} component with the following features:
          </p>
          <ul className="{"mt-4 space-y-2" if spec.styling == "tailwind" else "feature-list"}">
            {chr(123) + "".join([f"<li className=\"{'flex items-center' if spec.styling == 'tailwind' else 'feature-item'}\"><span className=\"{'text-green-500 mr-2' if spec.styling == 'tailwind' else 'checkmark'}\">✓</span>{req.title()}</li>" for req in spec.requirements]) + chr(125)}
          </ul>
        </section>
        
        {"<nav className=\"mt-6\"><Link to=\"/\" className=\"text-blue-600 hover:text-blue-800\">← Back to Home</Link></nav>" if "routing" in spec.requirements else ""}
      </main>
    </div>
  );
}};

{"// Loading Spinner Component" if "state" in spec.requirements else ""}
{"const LoadingSpinner = () => (" if "state" in spec.requirements else ""}
{"  <div className=\"flex items-center justify-center p-4\">" if "state" in spec.requirements else ""}
{"    <div className=\"animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600\"></div>" if "state" in spec.requirements else ""}
{"  </div>" if "state" in spec.requirements else ""}
{");" if "state" in spec.requirements else ""}

{"// Data Display Component" if "api" in spec.requirements else ""}
{"const DataDisplay = ({ data }) => (" if "api" in spec.requirements else ""}
{"  <div className=\"bg-gray-50 p-4 rounded\">" if "api" in spec.requirements else ""}
{"    <pre className=\"text-sm\">{JSON.stringify(data, null, 2)}</pre>" if "api" in spec.requirements else ""}
{"  </div>" if "api" in spec.requirements else ""}
{");" if "api" in spec.requirements else ""}

export default {name};
"""
        
        else:  # Class component
            return f"""// {name} Class Component - Generated by Multi-Agent Factory
import React, {{ Component }} from 'react';

class {name} extends Component {{
  constructor(props) {{
    super(props);
    this.state = {{
      data: null,
      loading: false
    }};
  }}

  componentDidMount() {{
    // Component initialization
    console.log('{name} component mounted');
  }}

  render() {{
    return (
      <div className="{name.lower()}-container">
        <h1>{name} Class Component</h1>
        <p>Generated with requirements: {", ".join(spec.requirements)}</p>
      </div>
    );
  }}
}}

export default {name};
"""
    
    def generate_tests(self, spec: ComponentSpec, name: str) -> str:
        """Generate test file for the component"""
        return f"""// {name} Component Tests - Generated by Multi-Agent Factory
import React from 'react';
import {{ render, screen, fireEvent, waitFor }} from '@testing-library/react';
import {{ MemoryRouter }} from 'react-router-dom';
import {name} from './{name}';

// Mock axios if API requirements exist
{"import axios from 'axios';" if "api" in spec.requirements else ""}
{"jest.mock('axios');" if "api" in spec.requirements else ""}
{"const mockedAxios = axios as jest.Mocked<typeof axios>;" if "api" in spec.requirements else ""}

const renderWithRouter = (component: React.ReactElement) => {{
  return render(
    <MemoryRouter>
      {{component}}
    </MemoryRouter>
  );
}};

describe('{name} Component', () => {{
  beforeEach(() => {{
    {"mockedAxios.get.mockResolvedValue({ data: { message: 'Test data' } });" if "api" in spec.requirements else ""}
  }});

  test('renders component without crashing', () => {{
    {"renderWithRouter(<" + name + " />);" if "routing" in spec.requirements else f"render(<{name} />);"}
    expect(screen.getByText('{name}')).toBeInTheDocument();
  }});

  test('displays component title', () => {{
    {"renderWithRouter(<" + name + " />);" if "routing" in spec.requirements else f"render(<{name} />);"}
    expect(screen.getByRole('heading', {{ level: 1 }})).toHaveTextContent('{name}');
  }});

  {"test('handles loading state correctly', async () => {" if "state" in spec.requirements else ""}
  {"  renderWithRouter(<" + name + " />) if 'routing' in spec.requirements else f'render(<{name} />);'" if "state" in spec.requirements else ""}
  {"  expect(screen.getByText(/loading/i)).toBeInTheDocument();" if "state" in spec.requirements else ""}
  {"  await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());" if "state" in spec.requirements else ""}
  {"});" if "state" in spec.requirements else ""}

  {"test('fetches and displays API data', async () => {" if "api" in spec.requirements else ""}
  {"  renderWithRouter(<" + name + " />) if 'routing' in spec.requirements else f'render(<{name} />);'" if "api" in spec.requirements else ""}
  {"  await waitFor(() => expect(mockedAxios.get).toHaveBeenCalledWith('/api/data'));" if "api" in spec.requirements else ""}
  {"  expect(screen.getByText(/test data/i)).toBeInTheDocument();" if "api" in spec.requirements else ""}
  {"});" if "api" in spec.requirements else ""}

  test('has proper accessibility attributes', () => {{
    {"renderWithRouter(<" + name + " />);" if "routing" in spec.requirements else f"render(<{name} />);"}
    const mainElement = screen.getByRole('main');
    expect(mainElement).toHaveAttribute('aria-label', 'Main content');
  }});
}});
"""
    
    def generate_styles(self, name: str) -> str:
        """Generate CSS styles for the component"""
        return f"""/* {name} Component Styles - Generated by Multi-Agent Factory */

.{name.lower()}-container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}}

.{name.lower()}-container .header {{
  margin-bottom: 2rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 1rem;
}}

.{name.lower()}-container .title {{
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
  margin: 0;
}}

.{name.lower()}-container .content {{
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}}

.{name.lower()}-container .section {{
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}}

.{name.lower()}-container .section-title {{
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #374151;
}}

.{name.lower()}-container .description {{
  color: #6b7280;
  line-height: 1.6;
}}

.{name.lower()}-container .feature-list {{
  list-style: none;
  padding: 0;
  margin-top: 1rem;
}}

.{name.lower()}-container .feature-item {{
  display: flex;
  align-items: center;
  padding: 0.5rem 0;
}}

.{name.lower()}-container .checkmark {{
  color: #10b981;
  margin-right: 0.5rem;
  font-weight: bold;
}}

/* Responsive Design */
@media (max-width: 768px) {{
  .{name.lower()}-container {{
    padding: 1rem;
  }}
  
  .{name.lower()}-container .title {{
    font-size: 1.5rem;
  }}
}}

/* Dark Mode Support */
@media (prefers-color-scheme: dark) {{
  .{name.lower()}-container {{
    background-color: #1f2937;
    color: #f9fafb;
  }}
  
  .{name.lower()}-container .section {{
    background-color: #374151;
  }}
  
  .{name.lower()}-container .title {{
    color: #f9fafb;
  }}
}}
"""
    
    async def update_task_status(self, task_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update task status in Redis"""
        if not self.redis_client:
            return
        
        try:
            task_data = self.redis_client.get(f"task:{task_id}")
            if task_data:
                data = json.loads(task_data)
                data["status"] = status
                data["updated_at"] = datetime.utcnow().isoformat()
                
                if result:
                    data["result"] = result
                if error:
                    data["error"] = error
                
                ttl = 3600 if status == "completed" else 300
                self.redis_client.setex(f"task:{task_id}", ttl, json.dumps(data))
                
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Failed to update task status: {e}")
    
    async def start_listening(self):
        """Start listening for tasks"""
        if not self.nats_client:
            raise Exception("NATS client not connected")
        
        subject = f"agent.{self.role}"
        await self.nats_client.subscribe(subject, cb=self.message_handler)
        logger.info(f"🎧 [{self.agent_id}] Listening on subject: {subject}")
        
        self.status = "listening"
        while True:
            await asyncio.sleep(1)
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info(f"🛑 [{self.agent_id}] Shutting down...")
        self.status = "shutting_down"
        
        if self.nats_client:
            await self.nats_client.drain()
        
        self.status = "stopped"

async def main():
    agent = FrontendDevAgent()
    
    try:
        await agent.connect()
        logger.info(f"🚀 [{agent.agent_id}] Frontend dev agent started")
        await agent.start_listening()
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Agent failed: {e}")
    finally:
        await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())


# Backend Developer Agent
# File: agents/backend_dev/agent.py
import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from nats.aio.client import Client as NATS
import redis
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BackendSpec:
    framework: str
    database: str
    api_style: str
    authentication: bool = True
    caching: bool = True
    testing: bool = True

class BackendDevAgent:
    def __init__(self, agent_id: str = "backend_dev_001"):
        self.agent_id = agent_id
        self.role = "backend_dev"
        self.status = "starting"
        self.processed_tasks = 0
        
        # Connections
        self.nats_client: Optional[NATS] = None
        self.redis_client: Optional[redis.Redis] = None
        self.db_connection_uri = os.getenv("POSTGRES_URI", "postgresql://user:pass@db:5432/factory")
        
    async def connect(self):
        """Initialize connections"""
        try:
            self.nats_client = NATS()
            nats_url = os.getenv("NATS_URL", "nats://nats:4222")
            await self.nats_client.connect(nats_url, max_reconnect_attempts=5)
            logger.info(f"✅ [{self.agent_id}] Connected to NATS")
            
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"✅ [{self.agent_id}] Connected to Redis")
            
            self.status = "ready"
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Connection failed: {e}")
            self.status = "error"
            raise
    
    async def message_handler(self, msg):
        """Handle incoming backend development tasks"""
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("task_id")
            
            logger.info(f"🔧 [{self.agent_id}] Received backend task: {task_id}")
            
            await self.update_task_status(task_id, "processing")
            result = await self.process_task(data)
            await self.update_task_status(task_id, "completed", result=result)
            
            self.processed_tasks += 1
            logger.info(f"✅ [{self.agent_id}] Completed backend task: {task_id}")
            
        except Exception as e:
            task_id = "unknown"
            try:
                data = json.loads(msg.data.decode())
                task_id = data.get("task_id", "unknown")
            except:
                pass
            
            logger.error(f"❌ [{self.agent_id}] Backend task {task_id} failed: {e}")
            await self.update_task_status(task_id, "failed", error=str(e))
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process backend development task"""
        self.status = "working"
        
        try:
            payload = task_data.get("payload", {})
            spec = BackendSpec(
                framework=payload.get("framework", "fastapi"),
                database=payload.get("database", "postgresql"),
                api_style=payload.get("api_style", "rest"),
                authentication=payload.get("authentication", True),
                caching=payload.get("caching", True),
                testing=payload.get("testing", True)
            )
            
            # Generate backend code
            api_code = self.generate_api_code(spec, payload.get("service_name", "Service"))
            
            # Generate database models
            models_code = self.generate_models(spec, payload.get("entities", ["User"]))
            
            # Generate tests
            tests_code = self.generate_tests(spec, payload.get("service_name", "Service")) if spec.testing else ""
            
            # Generate Docker configuration
            docker_config = self.generate_docker_config(spec, payload.get("service_name", "Service"))
            
            self.status = "ready"
            return {
                "api_code": api_code,
                "models": models_code,
                "tests": tests_code,
                "docker_config": docker_config,
                "framework": spec.framework,
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.status = "error"
            raise Exception(f"Backend development failed: {str(e)}")
    
    def generate_api_code(self, spec: BackendSpec, service_name: str) -> str:
        """Generate API code based on framework"""
        if spec.framework.lower() == "fastapi":
            return self.generate_fastapi_code(spec, service_name)
        elif spec.framework.lower() == "flask":
            return self.generate_flask_code(spec, service_name)
        elif spec.framework.lower() == "django":
            return self.generate_django_code(spec, service_name)
        else:
            return self.generate_fastapi_code(spec, service_name)  # Default
    
    def generate_fastapi_code(self, spec: BackendSpec, service_name: str) -> str:
        """Generate FastAPI application code"""
        imports = [
            "from fastapi import FastAPI, HTTPException, Depends, status",
            "from pydantic import BaseModel",
            "import os",
            "from datetime import datetime, timedelta",
            "from typing import List, Optional"
        ]
        
        if spec.authentication:
            imports.extend([
                "from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials",
                "import jwt",
                "from passlib.context import CryptContext"
            ])
        
        if spec.caching:
            imports.append("import redis")
        
        if spec.database == "postgresql":
            imports.extend([
                "import psycopg",
                "from contextlib import asynccontextmanager"
            ])
        
        auth_code = ""
        if spec.authentication:
            auth_code = '''
# Authentication setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
'''
        
        cache_code = ""
        if spec.caching:
            cache_code = '''
# Redis cache setup
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

def get_cache(key: str):
    return redis_client.get(key)

def set_cache(key: str, value: str, ttl: int = 300):
    return redis_client.setex(key, ttl, value)
'''
        
        return f'''# {service_name} API - Generated by Multi-Agent Factory
{chr(10).join(imports)}

{auth_code}

{cache_code}

# Database connection
DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://user:pass@localhost:5432/db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Starting {service_name} API...")
    yield
    # Shutdown
    print(f"🛑 Shutting down {service_name} API...")

app = FastAPI(
    title="{service_name} API",
    description="Generated backend service with {spec.framework}",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic models
class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Health check endpoint
@app.get("/")
def health_check():
    return {{
        "status": "ok",
        "service": "{service_name.lower()}",
        "timestamp": datetime.utcnow().isoformat()
    }}

# User endpoints
@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    """Create a new user"""
    # TODO: Implement user creation logic
    {"# Cache invalidation" if spec.caching else ""}
    {"set_cache(f\"user:{{user.username}}\", \"created\", ttl=60)" if spec.caching else ""}
    
    return {{
        "id": 1,
        "username": user.username,
        "email": user.email,
        "is_active": True,
        "created_at": datetime.utcnow()
    }}

@app.get("/users", response_model=List[User])
def get_users({"current_user: str = Depends(get_current_user)" if spec.authentication else ""}):
    """Get all users"""
    {"# Check cache first" if spec.caching else ""}
    {"cached_users = get_cache(\"users:all\")" if spec.caching else ""}
    {"if cached_users:" if spec.caching else ""}
    {"    return json.loads(cached_users)" if spec.caching else ""}
    
    # TODO: Implement user retrieval logic
    users = [
        {{
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "created_at": datetime.utcnow()
        }}
    ]
    
    {"# Cache the result" if spec.caching else ""}
    {"set_cache(\"users:all\", json.dumps(users, default=str), ttl=300)" if spec.caching else ""}
    
    return users

@app.get("/users/{{user_id}}", response_model=User)
def get_user(user_id: int{"" if not spec.authentication else ", current_user: str = Depends(get_current_user)"}):
    """Get user by ID"""
    {"# Check cache" if spec.caching else ""}
    {"cached_user = get_cache(f\"user:{{user_id}}\")" if spec.caching else ""}
    {"if cached_user:" if spec.caching else ""}
    {"    return json.loads(cached_user)" if spec.caching else ""}
    
    # TODO: Implement user retrieval by ID
    if user_id == 1:
        user = {{
            "id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "created_at": datetime.utcnow()
        }}
        {"set_cache(f\"user:{{user_id}}\", json.dumps(user, default=str), ttl=300)" if spec.caching else ""}
        return user
    
    raise HTTPException(status_code=404, detail="User not found")

{"# Authentication endpoints" if spec.authentication else ""}
{"@app.post(\"/auth/token\", response_model=Token)" if spec.authentication else ""}
{"def login(username: str, password: str):" if spec.authentication else ""}
{"    \"\"\"Login endpoint\"\"\"" if spec.authentication else ""}
{"    # TODO: Implement authentication logic" if spec.authentication else ""}
{"    if username == \"testuser\" and password == \"testpass\":" if spec.authentication else ""}
{"        access_token = create_access_token(data={\"sub\": username})" if spec.authentication else ""}
{"        return {\"access_token\": access_token, \"token_type\": \"bearer\"}" if spec.authentication else ""}
{"    raise HTTPException(" if spec.authentication else ""}
{"        status_code=status.HTTP_401_UNAUTHORIZED," if spec.authentication else ""}
{"        detail=\"Incorrect username or password\"" if spec.authentication else ""}
{"    )" if spec.authentication else ""}

# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {{
        "error": {{
            "code": exc.status_code,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }}
    }}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    def generate_models(self, spec: BackendSpec, entities: List[str]) -> str:
        """Generate database models"""
        if spec.database == "postgresql":
            return self.generate_postgresql_models(entities)
        elif spec.database == "mongodb":
            return self.generate_mongodb_models(entities)
        else:
            return self.generate_postgresql_models(entities)
    
    def generate_postgresql_models(self, entities: List[str]) -> str:
        """Generate PostgreSQL models using SQLAlchemy"""
        return f'''# Database Models - Generated by Multi-Agent Factory
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://user:pass@localhost:5432/db")

engine = create_engine(DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User Model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

{chr(10).join([f"""
# {entity} Model
class {entity}(Base):
    __tablename__ = "{entity.lower()}s"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
""" for entity in entities if entity != "User"])}

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)
'''
    
    def generate_tests(self, spec: BackendSpec, service_name: str) -> str:
        """Generate test file"""
        return f'''# {service_name} API Tests - Generated by Multi-Agent Factory
import pytest
from fastapi.testclient import TestClient
from main import app{"" if not spec.authentication else ", create_access_token"}
import json

client = TestClient(app)

{"# Test authentication helper" if spec.authentication else ""}
{"def get_auth_headers():" if spec.authentication else ""}
{"    token = create_access_token(data={\"sub\": \"testuser\"})" if spec.authentication else ""}
{"    return {\"Authorization\": f\"Bearer {{token}}\"}" if spec.authentication else ""}

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "{service_name.lower()}"

def test_create_user():
    """Test user creation"""
    user_data = {{
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "testpassword"
    }}
    
    response = client.post("/users", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert data["is_active"] is True

def test_get_users():
    """Test getting all users"""
    {"headers = get_auth_headers()" if spec.authentication else ""}
    response = client.get("/users"{"" if not spec.authentication else ", headers=headers"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_user_by_id():
    """Test getting user by ID"""
    {"headers = get_auth_headers()" if spec.authentication else ""}
    response = client.get("/users/1"{"" if not spec.authentication else ", headers=headers"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1

def test_get_nonexistent_user():
    """Test getting non-existent user"""
    {"headers = get_auth_headers()" if spec.authentication else ""}
    response = client.get("/users/999"{"" if not spec.authentication else ", headers=headers"})
    assert response.status_code == 404

{"def test_login():" if spec.authentication else ""}
{"    \"\"\"Test user login\"\"\"" if spec.authentication else ""}
{"    response = client.post(\"/auth/token\", json={\"username\": \"testuser\", \"password\": \"testpass\"})" if spec.authentication else ""}
{"    assert response.status_code == 200" if spec.authentication else ""}
{"    data = response.json()" if spec.authentication else ""}
{"    assert \"access_token\" in data" if spec.authentication else ""}
{"    assert data[\"token_type\"] == \"bearer\"" if spec.authentication else ""}

{"def test_invalid_login():" if spec.authentication else ""}
{"    \"\"\"Test invalid login\"\"\"" if spec.authentication else ""}
{"    response = client.post(\"/auth/token\", json={\"username\": \"wronguser\", \"password\": \"wrongpass\"})" if spec.authentication else ""}
{"    assert response.status_code == 401" if spec.authentication else ""}

{"def test_unauthorized_access():" if spec.authentication else ""}
{"    \"\"\"Test unauthorized access\"\"\"" if spec.authentication else ""}
{"    response = client.get(\"/users\")" if spec.authentication else ""}
{"    assert response.status_code == 403" if spec.authentication else ""}

# Performance tests
def test_api_response_time():
    """Test API response time"""
    import time
    start = time.time()
    response = client.get("/")
    end = time.time()
    
    assert response.status_code == 200
    assert (end - start) < 1.0  # Should respond within 1 second

# Integration tests
@pytest.mark.integration
def test_full_user_workflow():
    """Test complete user workflow"""
    # Create user
    user_data = {{
        "username": "workflow_user",
        "email": "workflow@example.com", 
        "password": "testpass"
    }}
    
    create_response = client.post("/users", json=user_data)
    assert create_response.status_code == 201
    
    {"# Login" if spec.authentication else ""}
    {"login_response = client.post(\"/auth/token\", json={\"username\": \"workflow_user\", \"password\": \"testpass\"})" if spec.authentication else ""}
    {"assert login_response.status_code == 200" if spec.authentication else ""}
    {"token = login_response.json()[\"access_token\"]" if spec.authentication else ""}
    
    {"# Get user with auth" if spec.authentication else ""}
    {"headers = {\"Authorization\": f\"Bearer {{token}}\"}" if spec.authentication else ""}
    {"user_response = client.get(\"/users/1\", headers=headers)" if spec.authentication else ""}
    {"assert user_response.status_code == 200" if spec.authentication else ""}
'''
    
    def generate_docker_config(self, spec: BackendSpec, service_name: str) -> str:
        """Generate Docker configuration"""
        return f'''# Dockerfile for {service_name} - Generated by Multi-Agent Factory
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/ || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

---
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
{"python-jose[cryptography]==3.3.0" if spec.authentication else ""}
{"passlib[bcrypt]==1.7.4" if spec.authentication else ""}
{"redis==5.0.1" if spec.caching else ""}
{"sqlalchemy==2.0.23" if spec.database == "postgresql" else ""}
{"psycopg2-binary==2.9.7" if spec.database == "postgresql" else ""}
{"pymongo==4.6.0" if spec.database == "mongodb" else ""}
pytest==7.4.3
httpx==0.25.2

---
# docker-compose.yml
version: '3.8'
services:
  {service_name.lower()}:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URI=postgresql://user:pass@db:5432/{service_name.lower()}
      {"- REDIS_HOST=redis" if spec.caching else ""}
      - JWT_SECRET=your-secret-key
    depends_on:
      - db
      {"- redis" if spec.caching else ""}
    
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: {service_name.lower()}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  {"redis:" if spec.caching else ""}
    {"image: redis:7-alpine" if spec.caching else ""}
    {"ports:" if spec.caching else ""}
      {"- \"6379:6379\"" if spec.caching else ""}

volumes:
  postgres_data:
'''
    
    async def update_task_status(self, task_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update task status in Redis"""
        if not self.redis_client:
            return
        
        try:
            task_data = self.redis_client.get(f"task:{task_id}")
            if task_data:
                data = json.loads(task_data)
                data["status"] = status
                data["updated_at"] = datetime.utcnow().isoformat()
                
                if result:
                    data["result"] = result
                if error:
                    data["error"] = error
                
                ttl = 3600 if status == "completed" else 300
                self.redis_client.setex(f"task:{task_id}", ttl, json.dumps(data))
                
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Failed to update task status: {e}")
    
    async def start_listening(self):
        """Start listening for tasks"""
        if not self.nats_client:
            raise Exception("NATS client not connected")
        
        subject = f"agent.{self.role}"
        await self.nats_client.subscribe(subject, cb=self.message_handler)
        logger.info(f"🎧 [{self.agent_id}] Listening on subject: {subject}")
        
        self.status = "listening"
        while True:
            await asyncio.sleep(1)
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info(f"🛑 [{self.agent_id}] Shutting down...")
        self.status = "shutting_down"
        
        if self.nats_client:
            await self.nats_client.drain()
        
        self.status = "stopped"

async def main():
    agent = BackendDevAgent()
    
    try:
        await agent.connect()
        logger.info(f"🚀 [{agent.agent_id}] Backend dev agent started")
        await agent.start_listening()
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Agent failed: {e}")
    finally:
        await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())


# QA Tester Agent
# File: agents/qa_tester/agent.py
import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from nats.aio.client import Client as NATS
import redis
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestSpec:
    test_type: str  # unit, integration, e2e, performance, security
    framework: str  # pytest, jest, cypress, selenium
    coverage_threshold: float = 80.0
    performance_budget: Dict[str, float] = None

class QATesterAgent:
    def __init__(self, agent_id: str = "qa_tester_001"):
        self.agent_id = agent_id
        self.role = "qa_tester"
        self.status = "starting"
        self.processed_tasks = 0
        
        self.nats_client: Optional[NATS] = None
        self.redis_client: Optional[redis.Redis] = None
        self.db_connection_uri = os.getenv("POSTGRES_URI", "postgresql://user:pass@db:5432/factory")
        
    async def connect(self):
        """Initialize connections"""
        try:
            self.nats_client = NATS()
            nats_url = os.getenv("NATS_URL", "nats://nats:4222")
            await self.nats_client.connect(nats_url, max_reconnect_attempts=5)
            logger.info(f"✅ [{self.agent_id}] Connected to NATS")
            
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"✅ [{self.agent_id}] Connected to Redis")
            
            self.status = "ready"
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Connection failed: {e}")
            self.status = "error"
            raise
    
    async def message_handler(self, msg):
        """Handle incoming QA testing tasks"""
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("task_id")
            
            logger.info(f"🧪 [{self.agent_id}] Received QA task: {task_id}")
            
            await self.update_task_status(task_id, "processing")
            result = await self.process_task(data)
            await self.update_task_status(task_id, "completed", result=result)
            
            self.processed_tasks += 1
            logger.info(f"✅ [{self.agent_id}] Completed QA task: {task_id}")
            
        except Exception as e:
            task_id = "unknown"
            try:
                data = json.loads(msg.data.decode())
                task_id = data.get("task_id", "unknown")
            except:
                pass
            
            logger.error(f"❌ [{self.agent_id}] QA task {task_id} failed: {e}")
            await self.update_task_status(task_id, "failed", error=str(e))
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process QA testing task"""
        self.status = "working"
        
        try:
            payload = task_data.get("payload", {})
            spec = TestSpec(
                test_type=payload.get("test_type", "unit"),
                framework=payload.get("framework", "pytest"),
                coverage_threshold=payload.get("coverage_threshold", 80.0),
                performance_budget=payload.get("performance_budget", {
                    "response_time_ms": 500,
                    "memory_mb": 100,
                    "cpu_percent": 50
                })
            )
            
            # Generate test plan
            test_plan = self.generate_test_plan(spec, payload)
            
            # Generate test code
            test_code = self.generate_test_code(spec, payload)
            
            # Generate test configuration
            test_config = self.generate_test_config(spec, payload)
            
            # Generate CI/CD integration
            ci_config = self.generate_ci_config(spec, payload)
            
            self.