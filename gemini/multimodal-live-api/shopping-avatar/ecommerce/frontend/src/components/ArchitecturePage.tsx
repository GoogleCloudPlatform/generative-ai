import { useState } from 'react';
import { 
  Box, 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  Button, 
  Tabs, 
  Tab, 
  Card, 
  CardContent, 
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import { 
  ArrowBack, 
  Schema, 
  Hub, 
  Bolt, 
  Storage, 
  ArrowForward, 
  Code,
  SwapHoriz,
  CheckCircleOutlined
} from '@mui/icons-material';

interface ArchitecturePageProps {
  navigate: (to: string) => void;
  themeConfig?: any;
}

export function ArchitecturePage({ navigate }: ArchitecturePageProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedFlowStep, setSelectedFlowStep] = useState<number | null>(null);
  const [selectedTable, setSelectedTable] = useState<number>(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const capabilities = [
    {
      title: "Real-Time Multimodal Voice & Video",
      description: "Low-latency streaming of PCM audio captures at 16-bit 24kHz. Intercepts local microphone streams, handles Voice Activity Detection (VAD) interruption, and outputs live digital avatar animation.",
      icon: <Bolt color="primary" sx={{ fontSize: 32 }} />,
      tag: "Live Audio / H.264 Video"
    },
    {
      title: "WebSocket Proxy & GCP Auth Gateway",
      description: "Upgrades browser connections to a secure socket proxy. Attaches temporary GCP OAuth Access Tokens dynamically, keeping API keys hidden from client-side inspectors.",
      icon: <SwapHoriz color="primary" sx={{ fontSize: 32 }} />,
      tag: "FastAPI / ADC Gateway"
    },
    {
      title: "Model Context Protocol (MCP) Server",
      description: "Standardized JSON-RPC 2.0 interface. Maps Gemini's functionCall events directly to local business logic like semantic catalog searches, cart addition, and checkout processing.",
      icon: <Hub color="primary" sx={{ fontSize: 32 }} />,
      tag: "JSON-RPC 2.0 Protocol"
    },
    {
      title: "Cloud Spanner Hybrid Storage",
      description: "Combines transactional relational database operations with advanced vector similarity search (ARRAY<FLOAT32>) and full-text indexes for search relevancy.",
      icon: <Storage color="primary" sx={{ fontSize: 32 }} />,
      tag: "Spanner DDL / Cosine Search"
    }
  ];

  const flowSteps = [
    {
      title: "1. Voice Input",
      actor: "User",
      description: "User speaks into microphone: 'Show me red running shoes'",
      file: "useAudioRecorder.ts",
      details: "Captures user microphone audio, downsamples it to 16-bit 24kHz PCM, and sends it over a local WebSocket."
    },
    {
      title: "2. Secure Proxy",
      actor: "FastAPI Proxy",
      description: "Backend proxy forwards audio to Gemini Live API",
      file: "websocket.py & auth.py",
      details: "Upgrades the connection, grabs temporary GCP credentials via Application Default Credentials (ADC), and passes them upstream safely."
    },
    {
      title: "3. Tool Decision",
      actor: "Vertex AI (Gemini)",
      description: "Gemini decides a database lookup tool is needed",
      file: "Gemini Live Session",
      details: "Gemini Live analyzes the request, triggers a functionCall event for 'search_products' with prompt terms."
    },
    {
      title: "4. MCP Catch",
      actor: "React Frontend",
      description: "Frontend catches functionCall and routes to local MCP API",
      file: "useMCPExecution.ts",
      details: "Intercepts functionCall from the socket loop, executes local fetch/POST JSON-RPC to '/api/mcp'."
    },
    {
      title: "5. Vector Search",
      actor: "MCP Server",
      description: "Backend generates embeddings & queries Cloud Spanner",
      file: "mcp.py & database.py",
      details: "Converts search query into a 768-dimension vector and runs a Cosine Distance Spanner query."
    },
    {
      title: "6. Render & Speak",
      actor: "Vera Assistant",
      description: "Gemini speaks response & frontend overlays product cards",
      file: "AvatarDisplay1P.tsx & App.tsx",
      details: "Renders product data cards visually in the store while simultaneously playing avatar animations synced to the streaming audio response."
    }
  ];

  const tables = [
    {
      name: "products",
      description: "Product catalog storing item descriptions, inventory levels, and text/image vector embeddings.",
      columns: [
        { name: "product_id", type: "STRING(50)", key: "PRIMARY KEY", desc: "Unique item identifier" },
        { name: "name", type: "STRING(255)", key: "", desc: "Display name of product" },
        { name: "description", type: "STRING(MAX)", key: "", desc: "Detailed item description text" },
        { name: "price", type: "NUMERIC", key: "", desc: "Exact retail transaction pricing" },
        { name: "inventory_level", type: "INT64", key: "", desc: "Physical inventory units left" },
        { name: "image_url", type: "STRING(MAX)", key: "", desc: "Public address of product image" },
        { name: "embedding", type: "ARRAY<FLOAT32>(vector_length=>768)", key: "", desc: "Semantic vector generated from name/description" },
        { name: "image_embedding", type: "ARRAY<FLOAT32>(vector_length=>1408)", key: "", desc: "Multimodal image representation vector" }
      ],
      indexes: "Full-text search index (TOKENLIST) constructed dynamically on name attribute."
    },
    {
      name: "shopping_carts",
      description: "Ephemeral user shopping carts isolate sessions for concurrent shoppers.",
      columns: [
        { name: "session_id", type: "STRING(100)", key: "PRIMARY KEY (1)", desc: "Unique shopper browser session reference" },
        { name: "product_id", type: "STRING(50)", key: "PRIMARY KEY (2)", desc: "Target product lookup identifier" },
        { name: "quantity", type: "INT64", key: "", desc: "Quantity added to cart by user" },
        { name: "updated_at", type: "TIMESTAMP", key: "", desc: "Last action timestamp with allow_commit_timestamp=true" }
      ],
      indexes: "Primary composite key (session_id, product_id)."
    },
    {
      name: "orders",
      description: "Parent ledger containing finalized customer checkouts.",
      columns: [
        { name: "order_id", type: "STRING(50)", key: "PRIMARY KEY", desc: "Unique transaction invoice number" },
        { name: "customer_id", type: "STRING(50)", key: "", desc: "Billing customer account link" },
        { name: "total_amount", type: "NUMERIC", key: "", desc: "Sum amount of order purchase" },
        { name: "created_at", type: "TIMESTAMP", key: "", desc: "Commit timestamp indicating checkout event time" }
      ],
      indexes: "Parent table of order_items (Interleaved relationship)."
    },
    {
      name: "order_items",
      description: "Line-items table interleaved inside parent orders to guarantee transaction isolation.",
      columns: [
        { name: "order_id", type: "STRING(50)", key: "PRIMARY KEY (1)", desc: "Link to parent order table" },
        { name: "product_id", type: "STRING(50)", key: "PRIMARY KEY (2)", desc: "Purchased product identifier" },
        { name: "quantity", type: "INT64", key: "", desc: "Items count purchased" },
        { name: "unit_price", type: "NUMERIC", key: "", desc: "Purchase value of item during transaction" }
      ],
      indexes: "INTERLEAVE IN PARENT orders ON DELETE CASCADE."
    },
    {
      name: "retailer_settings",
      description: "System config that dynamically drives the frontend style variables and model persona.",
      columns: [
        { name: "config_id", type: "STRING(50)", key: "PRIMARY KEY", desc: "Active retailer settings id" },
        { name: "retailer_name", type: "STRING(255)", key: "", desc: "Retailer brand name (e.g. Target, BestBuy)" },
        { name: "theme_config", type: "JSON", key: "", desc: "Dynamic design details (primary/secondary color, font, logo URL)" },
        { name: "assistant_persona", type: "STRING(50)", key: "", desc: "Vera tone setup (e.g., standard shopper vs teenager)" },
        { name: "updated_at", type: "TIMESTAMP", key: "", desc: "Last modification timestamp" }
      ],
      indexes: "Queried globally at route /api/config."
    }
  ];

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f8fafc', color: '#0f172a', display: 'flex', flexDirection: 'column' }}>
      {/* Modern Glassmorphic Header */}
      <Box sx={{ 
        bgcolor: 'rgba(255, 255, 255, 0.85)', 
        backdropFilter: 'blur(16px)',
        py: 2, 
        px: 4, 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        borderBottom: '1px solid rgba(226, 232, 240, 0.8)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: '900', letterSpacing: '-0.03em' }} color="primary">
            RETAIL ASSISTANT
          </Typography>
          <Chip 
            label="Architecture & System Design" 
            size="small" 
            sx={{ 
              fontWeight: 700, 
              fontSize: '0.75rem',
              bgcolor: 'rgba(0, 0, 0, 0.05)', 
              color: '#334155', 
              borderRadius: '12px' 
            }} 
          />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button 
            variant="outlined" 
            size="small" 
            startIcon={<ArrowBack />} 
            onClick={() => navigate('/')}
            color="inherit"
            sx={{ 
              borderColor: 'rgba(0,0,0,0.12)', 
              borderRadius: '20px', 
              fontSize: '0.8rem',
              px: 2,
              '&:hover': { borderColor: 'primary.main', bgcolor: 'rgba(0,0,0,0.02)' } 
            }}
          >
            Back to Store
          </Button>
        </Box>
      </Box>

      {/* Main Container */}
      <Container maxWidth="xl" sx={{ flexGrow: 1, py: 4, px: { xs: 2, md: 4 } }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" sx={{ fontWeight: '900', letterSpacing: '-0.03em', color: '#0f172a' }}>
            System Architecture & Specifications
          </Typography>
          <Typography variant="subtitle2" sx={{ color: '#64748b', mt: 0.5, fontWeight: '500' }}>
            Functional capabilities, transaction flow, and Cloud Spanner database schema
          </Typography>
        </Box>

        {/* Tab Controls */}
        <Box sx={{ borderBottom: '1px solid #e2e8f0', mb: 4 }}>
          <Tabs 
            value={activeTab} 
            onChange={handleTabChange}
            textColor="primary"
            indicatorColor="primary"
            sx={{
              '& .MuiTab-root': {
                textTransform: 'none',
                fontWeight: '700',
                fontSize: '0.95rem',
                minWidth: 120,
                color: '#64748b',
                '&.Mui-selected': {
                  color: '#0f172a'
                }
              },
              '& .MuiTabs-indicator': {
                height: 3,
                borderRadius: '3px 3px 0 0',
                bgcolor: 'primary.main'
              }
            }}
          >
            <Tab label="Capabilities" icon={<Bolt />} iconPosition="start" />
            <Tab label="System Flow" icon={<Hub />} iconPosition="start" />
            <Tab label="Database DDL" icon={<Schema />} iconPosition="start" />
          </Tabs>
        </Box>

        {/* Tab content 0: Capabilities */}
        {activeTab === 0 && (
          <Box>
            <Grid container spacing={3}>
              {capabilities.map((cap, idx) => (
                <Grid size={{ xs: 12, md: 6 }} key={idx}>
                  <Card 
                    elevation={0}
                    sx={{ 
                      height: '100%', 
                      bgcolor: '#ffffff', 
                      border: '1px solid #e2e8f0',
                      borderRadius: 4,
                      boxShadow: '0 4px 20px rgba(0,0,0,0.02)',
                      transition: 'all 0.25s ease',
                      '&:hover': {
                        transform: 'translateY(-3px)',
                        boxShadow: '0 12px 30px rgba(0,0,0,0.06)',
                        borderColor: '#cbd5e1'
                      }
                    }}
                  >
                    <CardContent sx={{ p: 3.5 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Box sx={{ bgcolor: 'rgba(0, 0, 0, 0.04)', p: 1.5, borderRadius: 3, display: 'flex' }}>
                          {cap.icon}
                        </Box>
                        <Chip 
                          label={cap.tag} 
                          size="small" 
                          sx={{ 
                            bgcolor: '#f1f5f9', 
                            color: '#334155', 
                            fontWeight: '700',
                            border: '1px solid #e2e8f0'
                          }} 
                        />
                      </Box>
                      <Typography variant="h6" sx={{ fontWeight: '800', mb: 1, color: '#0f172a' }}>
                        {cap.title}
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#64748b', lineHeight: 1.6 }}>
                        {cap.description}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            {/* Architecture Highlights */}
            <Paper elevation={0} sx={{ p: 4, mt: 4, bgcolor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 4, boxShadow: '0 4px 20px rgba(0,0,0,0.02)' }}>
              <Typography variant="h6" sx={{ fontWeight: '850', color: '#0f172a', mb: 2.5 }}>
                Key Functional Highlights
              </Typography>
              <Grid container spacing={4}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: '750', color: '#0f172a', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CheckCircleOutlined fontSize="small" color="primary" /> Multi-Persona Retail Simulator
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#64748b', lineHeight: 1.6 }}>
                    The backend supports switching retailers dynamically. Brand layouts and styles are generated dynamically, adapting colours, typography, and assistant personalities on the fly.
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: '750', color: '#0f172a', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CheckCircleOutlined fontSize="small" color="primary" /> Advanced Vector RAG Integration
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#64748b', lineHeight: 1.6 }}>
                    Executes hybrid transactional searches. Generates vector embeddings for user speech, matching them using cosine similarity in Cloud Spanner to recommend relevant products.
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: '750', color: '#0f172a', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CheckCircleOutlined fontSize="small" color="primary" /> Interruption-Resilient Design
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#64748b', lineHeight: 1.6 }}>
                    Real-time voice processing downsamples mic streams and streams them upstream. Client-side VAD (Voice Activity Detection) guarantees swift interruption response.
                  </Typography>
                </Grid>
              </Grid>
            </Paper>
          </Box>
        )}

        {/* Tab content 1: System Flow Sequence */}
        {activeTab === 1 && (
          <Box>
            <Typography variant="subtitle1" sx={{ color: '#64748b', mb: 3, textAlign: 'center' }}>
              Select a step in the sequence loop below to view components, code locations, and technical implementation details.
            </Typography>

            {/* Interactive Timeline Layout */}
            <Box sx={{ 
              display: 'flex', 
              flexDirection: { xs: 'column', lg: 'row' }, 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              bgcolor: '#ffffff', 
              borderRadius: 4, 
              border: '1px solid #e2e8f0',
              boxShadow: '0 4px 20px rgba(0,0,0,0.02)',
              p: 3.5, 
              mb: 4,
              gap: 2
            }}>
              {flowSteps.map((step, idx) => (
                <Box key={idx} sx={{ 
                  display: 'flex', 
                  flexDirection: { xs: 'column', lg: 'row' }, 
                  alignItems: 'center', 
                  width: '100%', 
                  position: 'relative' 
                }}>
                  {/* Step bubble */}
                  <Paper 
                    elevation={0}
                    onClick={() => setSelectedFlowStep(idx)}
                    sx={{ 
                      p: 2, 
                      cursor: 'pointer',
                      flexGrow: 1,
                      textAlign: 'center',
                      borderRadius: 3,
                      border: '1.5px solid',
                      borderColor: selectedFlowStep === idx ? 'primary.main' : '#e2e8f0',
                      bgcolor: selectedFlowStep === idx ? '#f8fafc' : '#ffffff',
                      color: '#0f172a',
                      boxShadow: selectedFlowStep === idx ? '0 4px 12px rgba(0,0,0,0.06)' : 'none',
                      transition: 'all 0.25s ease',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                        borderColor: 'primary.main',
                        bgcolor: '#f8fafc'
                      }
                    }}
                  >
                    <Typography variant="caption" sx={{ color: '#64748b', fontWeight: '800', display: 'block', mb: 0.5, textTransform: 'uppercase' }}>
                      {step.actor}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: '750', fontSize: '0.85rem' }}>
                      {step.title}
                    </Typography>
                  </Paper>
                  
                  {/* Arrow connector */}
                  {idx < flowSteps.length - 1 && (
                    <Box sx={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center', 
                      color: '#94a3b8',
                      py: { xs: 1, lg: 0 },
                      px: { xs: 0, lg: 1.5 },
                      transform: { xs: 'rotate(90deg)', lg: 'none' }
                    }}>
                      <ArrowForward fontSize="small" />
                    </Box>
                  )}
                </Box>
              ))}
            </Box>

            {/* Selected Step Technical Details Drawer/Card */}
            {selectedFlowStep !== null ? (
              <Card elevation={0} sx={{ bgcolor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 4, boxShadow: '0 4px 24px rgba(0,0,0,0.04)' }}>
                <CardContent sx={{ p: 4 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: '850', color: '#0f172a', display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Code color="primary" />
                      {flowSteps[selectedFlowStep].title} Details
                    </Typography>
                    <Chip label={flowSteps[selectedFlowStep].actor} size="small" sx={{ fontWeight: '700', bgcolor: '#f1f5f9', color: '#334155' }} />
                  </Box>
                  
                  <Typography variant="body1" sx={{ color: '#334155', fontWeight: '600', mb: 2 }}>
                    "{flowSteps[selectedFlowStep].description}"
                  </Typography>
                  
                  <Divider sx={{ borderColor: '#f1f5f9', my: 2 }} />
                  
                  <Grid container spacing={3}>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <Typography variant="caption" sx={{ textTransform: 'uppercase', fontWeight: '800', color: '#64748b' }}>
                        Code / Implementation File
                      </Typography>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', bgcolor: '#0f172a', color: '#38bdf8', p: 1.5, borderRadius: 2, mt: 1, wordBreak: 'break-all', fontSize: '0.85rem' }}>
                        {flowSteps[selectedFlowStep].file}
                      </Typography>
                    </Grid>
                    <Grid size={{ xs: 12, md: 8 }}>
                      <Typography variant="caption" sx={{ textTransform: 'uppercase', fontWeight: '800', color: '#64748b' }}>
                        Under the Hood
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#475569', lineHeight: 1.6, mt: 1 }}>
                        {flowSteps[selectedFlowStep].details}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ) : (
              <Box sx={{ textAlign: 'center', p: 5, border: '2px dashed #cbd5e1', bgcolor: '#ffffff', borderRadius: 4 }}>
                <Typography color="textSecondary">
                  Click on any step bubble above to explore step implementation details.
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {/* Tab content 2: Database schema DDL */}
        {activeTab === 2 && (
          <Box>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 4 }}>
                <Paper elevation={0} sx={{ p: 3, bgcolor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 4, boxShadow: '0 4px 20px rgba(0,0,0,0.02)', height: '100%' }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: '850', color: '#0f172a', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Storage color="primary" /> Cloud Spanner Table Select
                  </Typography>
                  <List sx={{ p: 0 }}>
                    {tables.map((tbl, idx) => (
                      <ListItemButton 
                        key={idx} 
                        onClick={() => setSelectedTable(idx)}
                        sx={{ 
                          borderRadius: 2.5, 
                          mb: 1, 
                          bgcolor: selectedTable === idx ? '#f1f5f9' : 'transparent',
                          border: '1px solid',
                          borderColor: selectedTable === idx ? '#cbd5e1' : 'transparent',
                          color: '#0f172a',
                          '&:hover': {
                            bgcolor: '#f8fafc'
                          }
                        }}
                      >
                        <ListItemIcon sx={{ color: selectedTable === idx ? 'primary.main' : '#64748b', minWidth: 36 }}>
                          <Schema fontSize="small" />
                        </ListItemIcon>
                        <ListItemText 
                          primary={<Typography sx={{ fontWeight: selectedTable === idx ? '800' : '600', fontSize: '0.9rem' }}>{tbl.name}</Typography>} 
                        />
                      </ListItemButton>
                    ))}
                  </List>
                </Paper>
              </Grid>

              <Grid size={{ xs: 12, md: 8 }}>
                {selectedTable !== null && selectedTable < tables.length ? (
                  <Paper elevation={0} sx={{ p: 4, bgcolor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 4, boxShadow: '0 4px 20px rgba(0,0,0,0.02)' }}>
                    <Box sx={{ mb: 2.5 }}>
                      <Typography variant="h5" sx={{ fontWeight: '900', color: '#0f172a', mb: 1 }}>
                        Table: {tables[selectedTable].name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#64748b', lineHeight: 1.5 }}>
                        {tables[selectedTable].description}
                      </Typography>
                    </Box>
                    
                    <TableContainer component={Box} sx={{ bgcolor: '#ffffff', borderRadius: 3, border: '1px solid #e2e8f0', mb: 3 }}>
                      <Table size="small">
                        <TableHead sx={{ bgcolor: '#f8fafc' }}>
                          <TableRow>
                            <TableCell sx={{ color: '#475569', fontWeight: '800', borderBottom: '1px solid #e2e8f0' }}>Column Name</TableCell>
                            <TableCell sx={{ color: '#475569', fontWeight: '800', borderBottom: '1px solid #e2e8f0' }}>Type</TableCell>
                            <TableCell sx={{ color: '#475569', fontWeight: '800', borderBottom: '1px solid #e2e8f0' }}>Constraint</TableCell>
                            <TableCell sx={{ color: '#475569', fontWeight: '800', borderBottom: '1px solid #e2e8f0' }}>Description</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {tables[selectedTable].columns.map((col, idx) => (
                            <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.02)' } }}>
                              <TableCell sx={{ color: '#0f172a', fontWeight: '750', borderBottom: '1px solid #f1f5f9' }}>{col.name}</TableCell>
                              <TableCell sx={{ color: '#0284c7', fontFamily: 'monospace', fontSize: '0.8rem', borderBottom: '1px solid #f1f5f9' }}>{col.type}</TableCell>
                              <TableCell sx={{ borderBottom: '1px solid #f1f5f9' }}>
                                {col.key && <Chip label={col.key} size="small" color="primary" sx={{ fontSize: '0.68rem', height: 18, fontWeight: '700' }} />}
                              </TableCell>
                              <TableCell sx={{ color: '#475569', fontSize: '0.85rem', borderBottom: '1px solid #f1f5f9' }}>{col.desc}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    {tables[selectedTable].indexes && (
                      <Box sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 3, border: '1px solid #e2e8f0' }}>
                        <Typography variant="caption" sx={{ fontWeight: '800', color: '#334155', display: 'block', mb: 0.5, textTransform: 'uppercase' }}>
                          Physical Relationship / Indexes
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#64748b' }}>
                          {tables[selectedTable].indexes}
                        </Typography>
                      </Box>
                    )}
                  </Paper>
                ) : (
                  <Box sx={{ textAlign: 'center', p: 6, border: '2px dashed #cbd5e1', bgcolor: '#ffffff', borderRadius: 4, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography color="textSecondary">
                      Select a database table from the list on the left to view structure detail.
                    </Typography>
                  </Box>
                )}
              </Grid>
            </Grid>
          </Box>
        )}

      </Container>
    </Box>
  );
}
