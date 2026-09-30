// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  Button, 
  TextField,
  IconButton, 
  Badge,
  CircularProgress,
  Checkbox,
  FormControlLabel,
  InputBase,
  Radio,
  RadioGroup,
  FormControl,
  FormLabel,
  Dialog,
  DialogContent,
  DialogActions,
  Rating,
  Select,
  MenuItem
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { 
  Mic, 
  MicOff, 
  Send, 
  ShoppingCart, 
  PlayArrow, 
  Stop,
  Videocam,
  VideocamOff,
  Schema,
  Add,
  Remove,
  Delete,
  PhoneIphone
} from '@mui/icons-material';

import { useGeminiLive } from './hooks/useGeminiLive';
import { useCamera } from './hooks/useCamera';
import { AvatarDisplay1P } from './components/AvatarDisplay1P';
import { ProductCard } from './components/ProductCard';
import { ArchitecturePage } from './components/ArchitecturePage';
import { MobileViewPage } from './components/MobileViewPage';
import { executeMCPTool } from './api/tools';
import './App.css';


// Simple state-based router client-side
function useSimpleRouter() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname);

  useEffect(() => {
    const handleLocationChange = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handleLocationChange);
    return () => window.removeEventListener('popstate', handleLocationChange);
  }, []);

  const navigate = (to: string) => {
    window.history.pushState({}, '', to);
    setCurrentPath(to);
  };

  return { currentPath, navigate };
}

export default function App() {
  const { currentPath, navigate } = useSimpleRouter();
  const [configData, setConfigData] = useState<any>(null);
  const [defaultProducts, setDefaultProducts] = useState<any[]>([]);
  const [progressStatus, setProgressStatus] = useState<any>(null);
  const [productsOffset, setProductsOffset] = useState<number>(0);
  const [hasMoreProducts, setHasMoreProducts] = useState<boolean>(true);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);

  const refreshConfig = () => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        setConfigData(data);
      })
      .catch(err => console.error('Failed to load API config:', err));
  };

  // Fetch the configuration (including theme setup)
  useEffect(() => {
    refreshConfig();
  }, []);

  // Poll background seeding status globally every 2 seconds
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch('/api/admin/status');
        const data = await res.json();
        setProgressStatus(data);
      } catch (err) {
        console.error('Failed to poll background status:', err);
      }
    };

    checkStatus();
    const intervalId = setInterval(checkStatus, 2000);
    return () => clearInterval(intervalId);
  }, []);

  // Fetch standard catalog products (re-fetch when configData resets)
  useEffect(() => {
    setProductsOffset(0);
    setHasMoreProducts(true);
    setIsLoadingMore(false);
    fetch('/api/products?limit=12&offset=0')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setDefaultProducts(data);
          if (data.length < 12) {
            setHasMoreProducts(false);
          }
        }
      })
      .catch(err => console.error('Failed to fetch products:', err));
  }, [configData]);

  const fetchMoreProducts = () => {
    if (isLoadingMore || !hasMoreProducts) return;
    setIsLoadingMore(true);
    const nextOffset = productsOffset + 12;
    fetch(`/api/products?limit=12&offset=${nextOffset}`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          if (data.length > 0) {
            setDefaultProducts((prev: any[]) => [...prev, ...data]);
            setProductsOffset(nextOffset);
          }
          if (data.length < 12) {
            setHasMoreProducts(false);
          }
        }
        setIsLoadingMore(false);
      })
      .catch(err => {
        console.error('Failed to fetch more products:', err);
        setIsLoadingMore(false);
      });
  };

  // Construct Material-UI theme dynamically from backend configuration
  const theme = createTheme({
    palette: {
      primary: {
        main: '#000000', // Permanently lock UI color to Black
      },
      secondary: {
        main: configData?.theme?.secondary || '#ffffff',
      },
    },
    typography: {
      fontFamily: configData?.theme?.font || 'Inter, sans-serif',
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            textTransform: 'none',
            fontWeight: 'bold',
          },
        },
      },
    },
  });

  if (currentPath === '/admin') {
    return (
      <ThemeProvider theme={theme}>
        <AdminPage 
          navigate={navigate} 
          themeConfig={configData?.theme} 
          progressStatus={progressStatus}
        />
      </ThemeProvider>
    );
  }

  if (currentPath === '/arch') {
    return (
      <ThemeProvider theme={theme}>
        <ArchitecturePage 
          navigate={navigate} 
          themeConfig={configData?.theme} 
        />
      </ThemeProvider>
    );
  }

  if (currentPath === '/mobile') {
    return (
      <ThemeProvider theme={theme}>
        <MobileViewPage 
          navigate={navigate} 
          products={defaultProducts} 
          configData={configData}
        />
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <MainStorePage 
        navigate={navigate} 
        configData={configData} 
        defaultProducts={defaultProducts}
        progressStatus={progressStatus}
        fetchMoreProducts={fetchMoreProducts}
        hasMoreProducts={hasMoreProducts}
        isLoadingMore={isLoadingMore}
        refreshConfig={refreshConfig}
      />
    </ThemeProvider>
  );
}

// ----------------------------------------------------
// 1. MAIN STORE SCREEN COMPONENT
// ----------------------------------------------------
interface MainStorePageProps {
  navigate: (to: string) => void;
  configData: any;
  defaultProducts: any[];
  progressStatus: any;
  fetchMoreProducts: () => void;
  hasMoreProducts: boolean;
  isLoadingMore: boolean;
  refreshConfig: () => void;
}

function MainStorePage({ 
  navigate, 
  configData, 
  defaultProducts, 
  progressStatus,
  fetchMoreProducts,
  hasMoreProducts,
  isLoadingMore,
  refreshConfig
}: MainStorePageProps) {
  const [textInput, setTextInput] = useState('');
  const [sessionId] = useState(`sess_${Math.random().toString(36).substring(2, 9)}`);

  const [selectedAvatar, setSelectedAvatar] = useState('Vera');
  const {
    connectionState,
    isRecording,
    messages,
    activeVisual,
    activeOverlay,
    isThinking,
    connect,
    disconnect,
    sendTextMessage,
    sendVideoFrame,
    config
  } = useGeminiLive('google_1p', sessionId, selectedAvatar);

  const [localCart, setLocalCart] = useState<any[]>([]);
  const [manualOverlay, setManualOverlay] = useState<'cart' | 'checkout' | 'products' | null>(null);
  const [manualOrderDetails, setManualOrderDetails] = useState<any | null>(null);

  const [localOrderDetails, setLocalOrderDetails] = useState<any | null>(null);
  useEffect(() => {
    if (activeVisual?.toolName === 'checkout_cart') {
      setLocalOrderDetails(activeVisual.data);
    }
  }, [activeVisual]);

  const orderDetails = localOrderDetails || manualOrderDetails;
  const isTeenager = configData?.theme?.persona === 'teenager';

  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);
  const [reviews, setReviews] = useState<any[]>([]);
  const [newReviewName, setNewReviewName] = useState('');
  const [newReviewRating, setNewReviewRating] = useState<number>(5);
  const [newReviewComment, setNewReviewComment] = useState('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  const [localProductsList, setLocalProductsList] = useState<any[]>([]);
  useEffect(() => {
    setLocalProductsList(defaultProducts);
  }, [defaultProducts]);

  const [localSearchResults, setLocalSearchResults] = useState<any[]>([]);
  useEffect(() => {
    if (activeVisual?.toolName === 'search_products') {
      const items = (activeVisual.data as any)?.items || activeVisual.data || [];
      setLocalSearchResults(items);
    }
  }, [activeVisual]);

  // Automatically open product detail modal when assistant talks about/looks up a product
  useEffect(() => {
    const productId = (activeVisual as any)?.arguments?.product_id;
    if (productId && ['get_product_details', 'get_product_reviews'].includes(activeVisual?.toolName || '')) {
      fetch(`/api/products/${productId}`)
        .then(res => res.json())
        .then(data => {
          setSelectedProduct(data);
        })
        .catch(err => console.error("Error fetching product details:", err));
    }
  }, [activeVisual]);


  // Fetch reviews when selectedProduct changes
  useEffect(() => {
    if (selectedProduct) {
      fetch(`/api/products/${selectedProduct.product_id}/reviews`)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) {
            setReviews(data);
          }
        })
        .catch(err => console.error("Error fetching reviews:", err));
    } else {
      setReviews([]);
    }
  }, [selectedProduct]);

  const handleSubmitReview = async () => {
    if (!selectedProduct || !newReviewName.trim() || !newReviewRating) return;
    setIsSubmittingReview(true);
    try {
      const res = await fetch(`/api/products/${selectedProduct.product_id}/reviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: newReviewName,
          rating: newReviewRating,
          comment: newReviewComment
        })
      });
      if (res.ok) {
        const data = await res.json();
        setReviews(prev => [data, ...prev]);

        // Calculate updated rating statistics locally
        const newCount = (selectedProduct.reviews_count || 0) + 1;
        const newAvg = (
          ((selectedProduct.rating || 0) * (selectedProduct.reviews_count || 0)) + newReviewRating
        ) / newCount;

        const updatedProd = {
          ...selectedProduct,
          rating: newAvg,
          reviews_count: newCount
        };

        setSelectedProduct(updatedProd);

        // Update lists so change is immediate in visual grid
        setLocalProductsList(prev => prev.map(p => p.product_id === selectedProduct.product_id ? updatedProd : p));
        setLocalSearchResults(prev => prev.map(p => p.product_id === selectedProduct.product_id ? updatedProd : p));

        // Reset inputs
        setNewReviewName('');
        setNewReviewRating(5);
        setNewReviewComment('');
      }
    } catch (err) {
      console.error("Failed to submit review:", err);
    } finally {
      setIsSubmittingReview(false);
    }
  };


  const currentOverlay = activeOverlay || manualOverlay;

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    if (target.scrollHeight - target.scrollTop <= target.clientHeight + 50) {
      if (!currentOverlay && hasMoreProducts) {
        fetchMoreProducts();
      }
    }
  };

  const {
    isActive: isCameraActive,
    videoRef: cameraVideoRef,
    startCamera,
    stopCamera
  } = useCamera((base64Frame) => {
    sendVideoFrame(base64Frame);
  });

  useEffect(() => {
    if (connectionState !== 'connected') {
      stopCamera();
    }
  }, [connectionState, stopCamera]);

  useEffect(() => {
    if (activeVisual && ['add_to_cart', 'update_cart_item', 'remove_from_cart', 'get_cart'].includes(activeVisual.toolName || '')) {
      const items = (activeVisual.data as any)?.items || [];
      setLocalCart(items);
    }
  }, [activeVisual]);

  const refreshCart = () => {
    executeMCPTool('get_cart', {}, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) {
          setLocalCart(data.items);
        }
      })
      .catch(err => console.error('Failed to sync cart:', err));
  };

  useEffect(() => {
    refreshCart();
  }, [sessionId]);

  useEffect(() => {
    setManualOverlay(null);
    setManualOrderDetails(null);
    if (connectionState !== 'connected') {
      setLocalSearchResults([]);
      setLocalOrderDetails(null);
      setSelectedProduct(null);
    }
  }, [connectionState]);

  const handleAddToCart = (productId: string) => {
    executeMCPTool('add_to_cart', { product_id: productId, quantity: 1 }, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) {
          setLocalCart(data.items);
        }
        setManualOverlay('cart');
      })
      .catch(err => console.error('Failed to add to cart:', err));
  };

  const handleUpdateQty = (productId: string, quantity: number) => {
    executeMCPTool('update_cart_item', { product_id: productId, quantity }, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) {
          setLocalCart(data.items);
        }
      })
      .catch(err => console.error('Failed to update quantity:', err));
  };

  const handleRemoveItem = (productId: string) => {
    executeMCPTool('remove_from_cart', { product_id: productId }, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) {
          setLocalCart(data.items);
        }
      })
      .catch(err => console.error('Failed to remove item:', err));
  };

  const handleCheckout = () => {
    executeMCPTool('checkout_cart', {}, 'google_1p', sessionId)
      .then((data: any) => {
        setManualOrderDetails(data);
        setManualOverlay('checkout');
        setLocalCart([]);
      })
      .catch(err => console.error('Failed to checkout:', err));
  };

  

  useEffect(() => {
    if (activeVisual?.toolName === 'change_theme') {
      refreshConfig();
    }
  }, [activeVisual, refreshConfig]);



  const handleSendText = () => {
    if (textInput.trim()) {
      sendTextMessage(textInput);
      setTextInput('');
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f8fafc', display: 'flex', flexDirection: 'column' }}>
      
      {/* Global Background Seeding Notification Bar */}
      {progressStatus?.is_running && (
        <Box 
          sx={{ 
            bgcolor: 'primary.main', 
            color: 'primary.contrastText', 
            py: 1, 
            px: 3, 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            gap: 2, 
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            zIndex: 1100
          }}
        >
          <CircularProgress size={14} color="inherit" />
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            Regenerating catalog database for "{progressStatus.message}"... 
            {progressStatus.current > 0 && ` Stage: ${progressStatus.stage.toUpperCase()} (${progressStatus.current}/${progressStatus.total})`}
          </Typography>
        </Box>
      )}

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
        <Typography variant="h5" sx={{ fontWeight: '900', letterSpacing: '-0.03em' }} color="primary">
          RETAIL ASSISTANT
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button 
            variant="outlined" 
            size="small" 
            startIcon={<Schema />} 
            onClick={() => navigate('/arch')}
            color="inherit"
            sx={{ 
              borderColor: 'rgba(0,0,0,0.12)', 
              borderRadius: '20px', 
              fontSize: '0.8rem',
              px: 2,
              '&:hover': { borderColor: 'primary.main', bgcolor: 'rgba(0,0,0,0.02)' } 
            }}
          >
            Architecture
          </Button>
          <Button 
            variant="outlined" 
            size="small" 
            startIcon={<PhoneIphone />} 
            onClick={() => navigate('/mobile')}
            color="inherit"
            sx={{ 
              borderColor: 'rgba(0,0,0,0.12)', 
              borderRadius: '20px', 
              fontSize: '0.8rem',
              px: 2,
              '&:hover': { borderColor: 'primary.main', bgcolor: 'rgba(0,0,0,0.02)' } 
            }}
          >
            Mobile View
          </Button>
          <IconButton 
            color="primary" 
            sx={{ bgcolor: 'rgba(0,0,0,0.02)', p: 1 }}
            onClick={() => setManualOverlay(prev => prev === 'cart' ? null : 'cart')}
          >
            <Badge badgeContent={localCart.length} color="error">
              <ShoppingCart fontSize="small" />
            </Badge>
          </IconButton>
        </Box>
      </Box>

      {/* Main Container */}
      <Container maxWidth="xl" sx={{ flexGrow: 1, my: 3, display: 'flex', flexDirection: 'column' }}>
        <Grid container spacing={3} sx={{ height: { md: 'calc(100vh - 140px)' }, minHeight: 'calc(100vh - 140px)' }}>
          
          {/* Left Column: Avatar (top) + Conversation (bottom) */}
          <Grid size={{ xs: 12, md: 4 }} sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2.5 }}>
            
            {/* Top Card: Avatar with clean portrait fit */}
            <Paper elevation={0} sx={{ 
              p: 2.5, 
              display: 'flex', 
              flexDirection: 'column', 
              borderRadius: 6, 
              border: '1px solid #e2e8f0', 
              bgcolor: '#ffffff',
              flex: '0 0 calc(52% - 10px)', 
              minHeight: 0,
              boxShadow: '0 4px 20px rgba(0,0,0,0.02)'
            }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: '800', display: 'flex', alignItems: 'center', gap: 1 }}>
                  {isTeenager ? `Assistant ${selectedAvatar} (Whatever...)` : `Assistant ${selectedAvatar} (Live)`}
                  {connectionState === 'connected' && (
                    <Box sx={{ 
                      width: 8, 
                      height: 8, 
                      bgcolor: '#2e7d32', 
                      borderRadius: '50%', 
                      boxShadow: '0 0 8px #2e7d32'
                    }} />
                  )}
                </Typography>
                <Select
                  size="small"
                  value={selectedAvatar}
                  disabled={connectionState !== 'disconnected'}
                  onChange={(e) => setSelectedAvatar(e.target.value)}
                  sx={{ height: 28, fontSize: '0.75rem', fontWeight: 700, borderRadius: 2 }}
                >
                  <MenuItem value="Vera">Vera (Realistic)</MenuItem>
                  <MenuItem value="Kira">Kira (Realistic)</MenuItem>
                  <MenuItem value="Ingrid">Ingrid (Realistic)</MenuItem>
                  <MenuItem value="Sam">Sam (Realistic)</MenuItem>
                  <MenuItem value="Jay">Jay (Realistic)</MenuItem>
                  <MenuItem value="Paul">Paul (Realistic)</MenuItem>
                  <MenuItem value="Ben">Ben (Stylized)</MenuItem>
                  <MenuItem value="Kai">Kai (Stylized)</MenuItem>
                  <MenuItem value="Carmen">Carmen (Stylized)</MenuItem>
                  <MenuItem value="Leo">Leo (Stylized)</MenuItem>
                  <MenuItem value="Piper">Piper (Stylized)</MenuItem>
                </Select>
              </Box>

              <Box sx={{ 
                flexGrow: 1, 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center',
                mb: 2, 
                minHeight: 0
              }}>
                <Box sx={{
                  height: '100%',
                  aspectRatio: '704 / 1280',
                  maxHeight: '100%',
                  bgcolor: '#0f172a',
                  borderRadius: 4,
                  overflow: 'hidden',
                  position: 'relative',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  boxShadow: '0 8px 32px rgba(0,0,0,0.12)'
                }}>
                  <AvatarDisplay1P 
                    status={
                      connectionState === 'connected' ? 'ready' : 
                      connectionState === 'connecting' ? 'initializing' : 'idle'
                    } 
                    useVertexAI={config?.useVertexAI}
                    avatarName={selectedAvatar}
                  />
                  {isCameraActive && (
                    <Box sx={{
                      position: 'absolute',
                      bottom: 12,
                      right: 12,
                      width: 90,
                      height: 90,
                      borderRadius: '50%',
                      overflow: 'hidden',
                      border: '2px solid rgba(255,255,255,0.8)',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                      zIndex: 10,
                      transform: 'scaleX(-1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      bgcolor: '#000'
                    }}>
                      <video 
                        ref={cameraVideoRef}
                        autoPlay
                        playsInline
                        muted
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover'
                        }}
                      />
                    </Box>
                  )}
                </Box>
              </Box>

              {connectionState !== 'connected' && (
                <Box sx={{ 
                  mb: 2, 
                  p: 1.5, 
                  bgcolor: 'rgba(0, 0, 0, 0.02)', 
                  borderRadius: 3, 
                  border: '1px solid rgba(0, 0, 0, 0.05)',
                  textAlign: 'center'
                }}>
                  <Typography variant="body2" sx={{ fontWeight: '800', mb: 0.5, fontSize: '0.82rem', color: 'text.primary' }}>
                    {isTeenager ? `Meet ${selectedAvatar}, your teenage helper (they smirk).` : `Meet ${selectedAvatar}, your personal shopper.`}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.3, fontSize: '0.72rem' }}>
                    Click <strong>"Start Shopping"</strong> below to start browsing the catalog and ordering items.
                  </Typography>
                </Box>
              )}
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2 }}>
                {connectionState !== 'connected' ? (
                  <Button 
                    variant="contained" 
                    color="primary" 
                    startIcon={<PlayArrow />} 
                    onClick={connect}
                    size="medium"
                    sx={{ borderRadius: '24px', px: 3, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
                  >
                    Start Shopping
                  </Button>
                ) : (
                  <Button 
                    variant="contained" 
                    color="error" 
                    startIcon={<Stop />} 
                    onClick={disconnect}
                    size="medium"
                    sx={{ borderRadius: '24px', px: 3 }}
                  >
                    End Session
                  </Button>
                )}
                
                {connectionState === 'connected' && (
                  <IconButton 
                    color={isRecording ? 'error' : 'default'} 
                    size="medium"
                    sx={{ 
                      bgcolor: isRecording ? 'rgba(211, 47, 47, 0.1)' : 'rgba(0,0,0,0.03)',
                      '&:hover': { bgcolor: isRecording ? 'rgba(211, 47, 47, 0.15)' : 'rgba(0,0,0,0.05)' }
                    }}
                  >
                    {isRecording ? <Mic /> : <MicOff />}
                  </IconButton>
                )}

                {connectionState === 'connected' && (
                  <IconButton 
                    color={isCameraActive ? 'success' : 'default'} 
                    size="medium"
                    onClick={isCameraActive ? stopCamera : startCamera}
                    sx={{ 
                      bgcolor: isCameraActive ? 'rgba(46, 125, 50, 0.1)' : 'rgba(0,0,0,0.03)',
                      '&:hover': { bgcolor: isCameraActive ? 'rgba(46, 125, 50, 0.15)' : 'rgba(0,0,0,0.05)' }
                    }}
                  >
                    {isCameraActive ? <Videocam /> : <VideocamOff />}
                  </IconButton>
                )}
              </Box>

            </Paper>

            {/* Bottom Card: Conversation with Chat Bubbles */}
            <Paper elevation={0} sx={{ 
              p: 2.5, 
              display: 'flex', 
              flexDirection: 'column', 
              borderRadius: 6, 
              border: '1px solid #e2e8f0', 
              bgcolor: '#ffffff',
              overflow: 'hidden', 
              flex: '0 0 calc(48% - 10px)', 
              minHeight: 0,
              boxShadow: '0 4px 20px rgba(0,0,0,0.02)'
            }}>
              <Typography variant="subtitle2" sx={{ color: 'text.secondary', fontWeight: '800', mb: 1.5 }}>
                Live Conversation
              </Typography>
              
              <Box 
                className="custom-scrollbar"
                sx={{ 
                  flexGrow: 1, 
                  overflowY: 'auto', 
                  mb: 2, 
                  bgcolor: '#f8fafc', 
                  borderRadius: 4, 
                  p: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 1.5
                }}
              >
                {messages.length === 0 ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.5 }}>
                    <Typography variant="body2" color="text.secondary">No conversation history yet</Typography>
                  </Box>
                ) : (
                  messages.map((msg) => {
                    const isUser = msg.sender === 'user';
                    return (
                      <Box
                        key={msg.id}
                        sx={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: isUser ? 'flex-end' : 'flex-start',
                          width: '100%'
                        }}
                      >
                        <Box
                          sx={{
                            bgcolor: isUser ? 'primary.main' : '#ffffff',
                            color: isUser ? 'primary.contrastText' : '#1e293b',
                            borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                            p: 1.5,
                            maxWidth: '85%',
                            boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
                            border: isUser ? 'none' : '1px solid #f1f5f9'
                          }}
                        >
                          <Typography variant="body2" sx={{ lineHeight: 1.4, fontWeight: '500' }}>
                            {msg.text}
                          </Typography>
                        </Box>
                      </Box>
                    );
                  })
                )}
                
                {isThinking && (
                  <Box sx={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={12} />
                    <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                      {isTeenager ? `${selectedAvatar} is thinking or smirking...` : `${selectedAvatar} is working...`}
                    </Typography>
                  </Box>
                )}
              </Box>

              {/* Chat Input Pill */}
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1, 
                bgcolor: '#f1f5f9', 
                borderRadius: '24px', 
                px: 2, 
                py: 0.5,
                border: '1px solid #e2e8f0'
              }}>
                <InputBase
                  fullWidth
                  placeholder="Type a message or speak..."
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendText()}
                  disabled={connectionState !== 'connected'}
                  sx={{ fontSize: '0.875rem' }}
                />
                <IconButton 
                  color="primary" 
                  onClick={handleSendText} 
                  disabled={connectionState !== 'connected' || !textInput.trim()}
                  size="small"
                  sx={{ bgcolor: 'primary.main', color: '#ffffff', '&:hover': { bgcolor: 'primary.dark' }, p: 0.75, width: 28, height: 28 }}
                >
                  <Send sx={{ fontSize: '0.85rem' }} />
                </IconButton>
              </Box>
            </Paper>
          </Grid>

          {/* Right Column: RAG Overlay Results / Products / Cart */}
          <Grid size={{ xs: 12, md: 8 }} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Paper 
              elevation={0} 
              className="custom-scrollbar" 
              onScroll={handleScroll}
              sx={{ 
                p: 3.5, 
                flexGrow: 1, 
                display: 'flex', 
                flexDirection: 'column', 
                borderRadius: 6, 
                border: '1px solid #e2e8f0', 
                bgcolor: '#ffffff',
                overflowY: 'auto',
                boxShadow: '0 4px 20px rgba(0,0,0,0.02)'
              }}
            >
              
              {currentOverlay === 'products' && localSearchResults && Array.isArray(localSearchResults) && (
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: '850', letterSpacing: '-0.02em', mb: 3 }}>
                    Recommended Products
                  </Typography>
                  <Grid container spacing={3.5}>
                    {localSearchResults.map((item: any, i: number) => (
                      <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={i}>
                        <ProductCard item={item} onAddToCart={handleAddToCart} onProductClick={setSelectedProduct} />
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              )}

              {currentOverlay === 'cart' && (
                <Box sx={{ p: 3.5, bgcolor: '#f8fafc', borderRadius: 5, border: '1px solid #e2e8f0' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Box sx={{ bgcolor: 'success.main', color: '#ffffff', borderRadius: '50%', width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <ShoppingCart sx={{ fontSize: '0.9rem' }} />
                      </Box>
                      <Typography variant="h6" sx={{ fontWeight: '850', color: 'text.primary', letterSpacing: '-0.01em' }}>
                        Shopping Cart
                      </Typography>
                    </Box>
                    <Button 
                      variant="text" 
                      color="inherit" 
                      onClick={() => setManualOverlay(null)}
                      sx={{ textTransform: 'none', fontWeight: 'bold' }}
                    >
                      Close
                    </Button>
                  </Box>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {localCart.length > 0 ? (
                      <>
                        {localCart.map((item: any, i: number) => (
                          <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, bgcolor: '#ffffff', borderRadius: 3, boxShadow: '0 2px 6px rgba(0,0,0,0.02)', border: '1px solid #f1f5f9' }}>
                            <Box>
                              <Typography sx={{ fontWeight: 'bold', fontSize: '0.95rem' }}>{item.name}</Typography>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                                <Typography variant="caption" color="text.secondary">Qty: </Typography>
                                <IconButton 
                                  size="small" 
                                  onClick={() => handleUpdateQty(item.product_id, item.quantity - 1)}
                                  sx={{ p: 0.25, border: '1px solid #cbd5e1' }}
                                >
                                  <Remove sx={{ fontSize: '0.8rem' }} />
                                </IconButton>
                                <Typography variant="body2" sx={{ fontWeight: 'bold', minWidth: 16, textAlign: 'center' }}>
                                  {item.quantity}
                                </Typography>
                                <IconButton 
                                  size="small" 
                                  onClick={() => handleUpdateQty(item.product_id, item.quantity + 1)}
                                  sx={{ p: 0.25, border: '1px solid #cbd5e1' }}
                                >
                                  <Add sx={{ fontSize: '0.8rem' }} />
                                </IconButton>
                              </Box>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                              <Typography sx={{ fontWeight: '800', color: 'primary.main' }}>${item.price}</Typography>
                              <IconButton 
                                size="small" 
                                color="error" 
                                onClick={() => handleRemoveItem(item.product_id)}
                              >
                                <Delete fontSize="small" />
                              </IconButton>
                            </Box>
                          </Box>
                        ))}
                        <Box sx={{ borderTop: '1px dashed #cbd5e1', pt: 2, mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography sx={{ fontWeight: 'bold' }}>Est. Subtotal</Typography>
                          <Typography variant="h6" sx={{ fontWeight: '900', color: 'primary.main' }}>
                            ${localCart.reduce((acc: number, item: any) => acc + (parseFloat(item.price) * (item.quantity || 1)), 0).toFixed(2)}
                          </Typography>
                        </Box>
                        <Button
                          variant="contained"
                          color="success"
                          fullWidth
                          onClick={handleCheckout}
                          sx={{ mt: 2.5, borderRadius: '24px', fontWeight: 'bold', py: 1 }}
                        >
                          Checkout Order
                        </Button>
                      </>
                    ) : (
                      <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>Your shopping cart is empty.</Typography>
                    )}
                  </Box>
                </Box>
              )}

              {currentOverlay === 'checkout' && orderDetails && (
                <Box sx={{ p: 4, bgcolor: '#ffffff', borderRadius: 5, border: '1px solid #f1f5f9', boxShadow: '0 10px 30px rgba(0,0,0,0.04)', textAlign: 'center', maxWidth: 500, mx: 'auto', my: 4 }}>
                  <Box sx={{ display: 'inline-flex', bgcolor: 'success.main', color: '#ffffff', borderRadius: '50%', width: 56, height: 56, alignItems: 'center', justifyContent: 'center', mb: 2.5 }}>
                    <Typography variant="h5" sx={{ fontWeight: 'bold' }}>✓</Typography>
                  </Box>
                  <Typography variant="h5" sx={{ color: 'text.primary', fontWeight: '850', mb: 1, letterSpacing: '-0.02em' }}>
                    Order Confirmed!
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3.5 }}>
                    Order ID: <strong>{orderDetails.order_id}</strong>
                  </Typography>
                  <Box sx={{ bgcolor: '#f8fafc', p: 2, borderRadius: 3, mb: 3.5 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textTransform: 'uppercase', fontWeight: 'bold', mb: 0.5 }}>
                      Total Charged
                    </Typography>
                    <Typography variant="h5" color="primary" sx={{ fontWeight: '900' }}>
                      ${orderDetails.total_amount}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ px: 2 }}>
                    Thank you for shopping with us! A receipt has been sent to your registered email address.
                  </Typography>
                </Box>
              )}

              {!currentOverlay && (
                <Box>
                  {/* Meet Vera banner moved to sidebar */}
                  
                  <Typography variant="h6" sx={{ fontWeight: '850', letterSpacing: '-0.02em', mb: 3 }}>
                    Featured Products
                  </Typography>
                  {localProductsList.length > 0 ? (
                    <>
                      <Grid container spacing={3.5}>
                        {localProductsList.map((item: any, i: number) => (
                          <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={i}>
                            <ProductCard item={item} onAddToCart={handleAddToCart} onProductClick={setSelectedProduct} />
                          </Grid>
                        ))}
                      </Grid>
                      {isLoadingMore && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                          <CircularProgress size={24} />
                        </Box>
                      )}
                    </>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Loading featured products...
                    </Typography>
                  )}
                </Box>
              )}
            </Paper>
          </Grid>
          
        </Grid>
      </Container>
      {/* Product Detail Modal */}
      <Dialog 
        open={Boolean(selectedProduct)} 
        onClose={() => setSelectedProduct(null)}
        maxWidth="md"
        fullWidth
        slotProps={{
          paper: {
            sx: { borderRadius: 6, p: 1 }
          }
        }}
      >
        {selectedProduct && (
          <>
            <DialogContent dividers sx={{ overflowY: 'auto', maxHeight: '65vh' }}>
              <Grid container spacing={4}>
                {/* Left Column: Product Image */}
                <Grid size={{ xs: 12, md: 6 }}>
                  {selectedProduct.image_url && (
                    <Box 
                      component="img" 
                      src={selectedProduct.image_url} 
                      alt={selectedProduct.name}
                      sx={{ 
                        width: '100%', 
                        height: 'auto', 
                        maxHeight: 380, 
                        objectFit: 'cover', 
                        borderRadius: 4,
                        border: '1px solid #e2e8f0'
                      }}
                    />
                  )}
                </Grid>

                {/* Right Column: Title, Rating, Price, Description, Buy */}
                <Grid size={{ xs: 12, md: 6 }} sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: '805', mb: 1, letterSpacing: '-0.02em', lineHeight: 1.2 }}>
                      {selectedProduct.name}
                    </Typography>
                    
                    {/* Rating Header */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <Rating 
                        value={selectedProduct.rating || 0} 
                        precision={0.1} 
                        readOnly 
                        size="medium" 
                      />
                      <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                        {selectedProduct.rating ? selectedProduct.rating.toFixed(1) : '0.0'} ({selectedProduct.reviews_count || 0} reviews)
                      </Typography>
                    </Box>

                    <Typography variant="h4" color="primary" sx={{ fontWeight: '900', mb: 2 }}>
                      ${selectedProduct.price}
                    </Typography>

                    <Typography variant="body1" color="text.secondary" sx={{ mb: 3, lineHeight: 1.6 }}>
                      {selectedProduct.description}
                    </Typography>
                  </Box>

                  <Box>
                    <Button
                      variant="contained"
                      color="primary"
                      fullWidth
                      onClick={() => handleAddToCart(selectedProduct.product_id)}
                      sx={{ borderRadius: '24px', py: 1.5, fontWeight: 'bold', fontSize: '1rem' }}
                    >
                      Add to Shopping Cart
                    </Button>
                  </Box>
                </Grid>
              </Grid>

              {/* Reviews Section */}
              <Box sx={{ mt: 5, borderTop: '1px solid #e2e8f0', pt: 4 }}>
                <Typography variant="h6" sx={{ fontWeight: '800', mb: 3 }}>
                  Customer Reviews
                </Typography>

                {/* Review Form */}
                <Box sx={{ bgcolor: '#f8fafc', p: 3, borderRadius: 4, border: '1px solid #e2e8f0', mb: 4 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 2 }}>
                    Write a Review
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Your Name"
                        size="small"
                        value={newReviewName}
                        onChange={(e) => setNewReviewName(e.target.value)}
                        disabled={isSubmittingReview}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold' }}>Rating:</Typography>
                      <Rating
                        value={newReviewRating}
                        onChange={(_, val) => setNewReviewRating(val || 5)}
                        disabled={isSubmittingReview}
                      />
                    </Grid>
                    <Grid size={{ xs: 12 }}>
                      <TextField
                        fullWidth
                        multiline
                        rows={2}
                        label="Review Comments"
                        placeholder="Tell others what you think about this product..."
                        size="small"
                        value={newReviewComment}
                        onChange={(e) => setNewReviewComment(e.target.value)}
                        disabled={isSubmittingReview}
                      />
                    </Grid>
                    <Grid size={{ xs: 12 }} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <Button
                        variant="contained"
                        onClick={handleSubmitReview}
                        disabled={isSubmittingReview || !newReviewName.trim()}
                        sx={{ borderRadius: '20px', px: 4 }}
                      >
                        {isSubmittingReview ? 'Submitting...' : 'Submit Review'}
                      </Button>
                    </Grid>
                  </Grid>
                </Box>

                {/* Reviews List */}
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, maxHeight: 300, overflowY: 'auto', pr: 1 }} className="custom-scrollbar">
                  {reviews.length > 0 ? (
                    reviews.map((rev: any) => (
                      <Box 
                        key={rev.review_id}
                        sx={{ 
                          p: 2, 
                          bgcolor: '#ffffff', 
                          borderRadius: 3, 
                          border: '1px solid #e2e8f0',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.01)'
                        }}
                      >
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            {rev.customer_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {rev.created_at ? new Date(rev.created_at).toLocaleDateString() : ''}
                          </Typography>
                        </Box>
                        <Rating 
                          value={rev.rating} 
                          readOnly 
                          size="small" 
                          sx={{ mb: 1, fontSize: '0.85rem' }} 
                        />
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.4 }}>
                          {rev.comment}
                        </Typography>
                      </Box>
                    ))
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', textAlign: 'center', py: 2 }}>
                      No reviews yet for this product. Be the first to write one!
                    </Typography>
                  )}
                </Box>
              </Box>
            </DialogContent>
            <DialogActions sx={{ p: 2, borderTop: '1px solid #e2e8f0' }}>
              <Button onClick={() => setSelectedProduct(null)} color="inherit" sx={{ fontWeight: 'bold' }}>
                Close Window
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}

// ----------------------------------------------------
// 2. ADMIN PORTAL SCREEN COMPONENT
// ----------------------------------------------------
interface AdminPageProps {
  navigate: (to: string) => void;
  themeConfig: any;
  progressStatus: any;
}

function AdminPage({ navigate, themeConfig, progressStatus }: AdminPageProps) {
  const [retailer, setRetailer] = useState('');
  const [productsCount, setProductsCount] = useState(15);
  const [customersCount, setCustomersCount] = useState(50);
  const [ordersCount, setOrdersCount] = useState(100);
  const [truncateDb, setTruncateDb] = useState(false);
  const [populateDb, setPopulateDb] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [logs, setLogs] = useState<string[]>([]);
  const [persona, setPersona] = useState('shopper');

  useEffect(() => {
    if (themeConfig?.name) {
      setRetailer(themeConfig.name);
    }
    if (themeConfig?.persona) {
      setPersona(themeConfig.persona);
    }
  }, [themeConfig]);
  const [category, setCategory] = useState('');
  
  const currentRetailer = themeConfig?.name || 'Retail';

  // Keep isSubmitting state synchronized with backend status
  useEffect(() => {
    if (progressStatus?.is_running) {
      setIsSubmitting(true);
      setStatusMsg(progressStatus.message);
    } else if (isSubmitting && progressStatus?.stage === 'complete') {
      setStatusMsg('Catalog generation finished successfully! Redirecting...');
      const timer = setTimeout(() => {
        window.location.href = '/';
      }, 2000);
      return () => clearTimeout(timer);
    } else if (progressStatus && !progressStatus.is_running) {
      setIsSubmitting(false);
    }
  }, [progressStatus, isSubmitting]);

  // Poll execution logs from backend in real-time when a job is active
  useEffect(() => {
    let intervalId: any;
    
    const fetchLogs = async () => {
      try {
        const res = await fetch('/api/admin/logs');
        const data = await res.json();
        if (data && Array.isArray(data.logs)) {
          setLogs(data.logs);
        }
      } catch (err) {
        console.error('Failed to retrieve logs:', err);
      }
    };

    if (isSubmitting) {
      fetchLogs();
      intervalId = setInterval(fetchLogs, 1500);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isSubmitting]);

  const handleSubmit = async () => {
    if (!retailer.trim()) return;
    setIsSubmitting(true);
    
    let msg = `Updating retailer configuration to '${retailer}'...`;
    if (truncateDb) msg = `Truncating Spanner database tables...`;
    if (populateDb) msg = `Initializing catalog generation using Gemini...`;
    setStatusMsg(msg);
    setLogs(['Initializing background subprocess...']);
    
    try {
      const res = await fetch('/api/admin/retailer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          retailer,
          products_count: populateDb ? productsCount : 0,
          customers_count: populateDb ? customersCount : 0,
          orders_count: populateDb ? ordersCount : 0,
          truncate_db: truncateDb,
          category: populateDb ? category.trim() : "",
          persona: persona
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMsg('Database changes requested. Seeding background job initiated...');
      } else {
        setStatusMsg(`Error: ${data.message}`);
        setIsSubmitting(false);
      }
    } catch (err) {
      console.error(err);
      setStatusMsg('Failed to connect to backend server admin endpoint.');
      setIsSubmitting(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f4f6f9', display: 'flex', alignItems: 'center', justifyContent: 'center', p: 3 }}>
      <Paper elevation={4} sx={{ p: 4, width: '100%', maxWidth: 520, borderRadius: 6 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 1, textAlign: 'center' }}>
          Retailer Admin Portal
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4, textAlign: 'center' }}>
          Manage the active retailer settings, customize the database tables, and control product catalog seeding.
        </Typography>

        <Box sx={{ mb: 3, p: 2, bgcolor: '#f1f3f4', borderRadius: 3, border: '1px solid #e0e0e0' }}>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 'bold' }}>
            Current Active Retailer
          </Typography>
          <Typography variant="body1" sx={{ fontWeight: 'bold', color: 'primary.main', mt: 0.5 }}>
            {currentRetailer}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
          <TextField
            fullWidth
            label="New Retailer Name"
            placeholder="e.g. Target, Best Buy, Sephora, IKEA"
            value={retailer}
            onChange={(e) => setRetailer(e.target.value)}
            disabled={isSubmitting}
          />

          <FormControl component="fieldset" disabled={isSubmitting} sx={{ display: 'flex', flexDirection: 'column', border: '1px solid #e0e0e0', borderRadius: 3, p: 2, bgcolor: '#fafafa' }}>
            <FormLabel component="legend" sx={{ fontWeight: 'bold', fontSize: '0.875rem', mb: 1, color: 'text.primary' }}>
              Assistant Persona
            </FormLabel>
            <RadioGroup
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}
            >
              <FormControlLabel 
                value="shopper" 
                control={<Radio size="small" />} 
                label={
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>Helpful Shopper</Typography>
                    <Typography variant="caption" color="text.secondary">Friendly, polite e-commerce personal shopper.</Typography>
                  </Box>
                }
                sx={{ alignItems: 'flex-start', margin: 0 }}
              />
              <FormControlLabel 
                value="teenager" 
                control={<Radio size="small" />} 
                label={
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>Disgruntled Teenager</Typography>
                    <Typography variant="caption" color="text.secondary">Sassy, reluctant assistant who smirks and says "Yasss Queeen".</Typography>
                  </Box>
                }
                sx={{ alignItems: 'flex-start', margin: 0 }}
              />
            </RadioGroup>
          </FormControl>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', border: '1px solid #e0e0e0', borderRadius: 3, p: 2, bgcolor: '#fafafa' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
              Database Operations
            </Typography>
            
            <FormControlLabel
              control={
                <Checkbox 
                  checked={truncateDb} 
                  onChange={(e) => setTruncateDb(e.target.checked)} 
                  disabled={isSubmitting}
                />
              }
              label={
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>Truncate Spanner Tables</Typography>
                  <Typography variant="caption" color="text.secondary">Deletes all current products, carts, and order history.</Typography>
                </Box>
              }
              sx={{ mb: 1 }}
            />

            <FormControlLabel
              control={
                <Checkbox 
                  checked={populateDb} 
                  onChange={(e) => setPopulateDb(e.target.checked)} 
                  disabled={isSubmitting}
                />
              }
              label={
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>Populate Catalog Data</Typography>
                  <Typography variant="caption" color="text.secondary">Seeds Spanner database with products using Gemini & Faker.</Typography>
                </Box>
              }
            />

            {populateDb && (
              <Box sx={{ mt: 2, pl: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label="Products"
                    type="number"
                    size="small"
                    value={productsCount}
                    onChange={(e) => setProductsCount(Math.max(1, parseInt(e.target.value) || 1))}
                    disabled={isSubmitting}
                    sx={{ width: '33%' }}
                  />
                  <TextField
                    label="Customers"
                    type="number"
                    size="small"
                    value={customersCount}
                    onChange={(e) => setCustomersCount(Math.max(1, parseInt(e.target.value) || 1))}
                    disabled={isSubmitting}
                    sx={{ width: '33%' }}
                  />
                  <TextField
                    label="Orders"
                    type="number"
                    size="small"
                    value={ordersCount}
                    onChange={(e) => setOrdersCount(Math.max(0, parseInt(e.target.value) || 0))}
                    disabled={isSubmitting}
                    sx={{ width: '33%' }}
                  />
                </Box>
                <TextField
                  fullWidth
                  label="Product Category (Optional)"
                  placeholder="e.g. Home Decor, Electronics, Apparel"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  disabled={isSubmitting}
                  size="small"
                  sx={{ mt: 1 }}
                />
              </Box>
            )}
          </Box>
          
          {statusMsg && (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1, my: 1 }}>
              {isSubmitting && <CircularProgress size={20} />}
              <Typography variant="body2" sx={{ textAlign: 'center', fontStyle: 'italic', color: 'primary.main', mt: 1 }}>
                {statusMsg}
              </Typography>
              {progressStatus?.is_running && progressStatus.current > 0 && (
                <Typography variant="caption" color="text.secondary">
                  Progress stage: {progressStatus.stage.toUpperCase()} ({progressStatus.current}/{progressStatus.total})
                </Typography>
              )}
            </Box>
          )}

          {/* Terminal Sim Shell Output Logging Viewer */}
          {logs.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, color: 'text.secondary' }}>
                Shell Execution Logs
              </Typography>
              <Paper 
                elevation={2} 
                sx={{ 
                  p: 1.5, 
                  bgcolor: '#1e1e1e', 
                  color: '#d4d4d4', 
                  fontFamily: 'monospace', 
                  fontSize: '11px', 
                  height: 180, 
                  overflowY: 'auto',
                  borderRadius: 3,
                  whiteSpace: 'pre-wrap',
                  display: 'flex',
                  flexDirection: 'column-reverse' // auto-scrolls to the bottom
                }}
              >
                <Box>
                  {logs.map((line, idx) => (
                    <div key={idx} style={{ borderBottom: '1px solid #2e2e2e', padding: '2px 0' }}>{line}</div>
                  ))}
                </Box>
              </Paper>
            </Box>
          )}

          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <Button
              fullWidth
              variant="outlined"
              onClick={() => navigate('/')}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              fullWidth
              variant="contained"
              color="primary"
              onClick={handleSubmit}
              disabled={isSubmitting || !retailer.trim()}
            >
              Apply Changes
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
}
