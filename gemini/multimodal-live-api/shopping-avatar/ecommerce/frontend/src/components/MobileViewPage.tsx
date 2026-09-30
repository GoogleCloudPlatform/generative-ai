import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  IconButton, 
  Card, 
  CardContent, 
  CardMedia, 
  Chip, 
  Badge, 
  Dialog, 
  Select, 
  MenuItem, 
  Drawer,
  CircularProgress
} from '@mui/material';
import { 
  ArrowBack, 
  Home, 
  ShoppingCart, 
  Person, 
  Star, 
  Close, 
  AddShoppingCart,
  Wifi,
  BatteryFull,
  SignalCellularAlt,
  GraphicEq,
  PlayArrow,
  Stop,
  Videocam,
  VideocamOff,
  ExpandMore,
  ExpandLess,
  AutoAwesome,
  CheckCircle,
  Delete,
  Add,
  Remove
} from '@mui/icons-material';
import { useGeminiLive } from '../hooks/useGeminiLive';
import { useCamera } from '../hooks/useCamera';
import { AvatarDisplay1P } from './AvatarDisplay1P';
import { executeMCPTool } from '../api/tools';

interface MobileViewPageProps {
  navigate: (to: string) => void;
  products: any[];
  configData?: any;
}

export function MobileViewPage({ navigate, products: initialProducts }: MobileViewPageProps) {
  const [products, setProducts] = useState<any[]>(initialProducts || []);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);
  const [activeBottomTab, setActiveBottomTab] = useState<number>(0);
  const [isAiExpanded, setIsAiExpanded] = useState<boolean>(true);

  // Live Assistant State
  const [sessionId] = useState(`mob_${Math.random().toString(36).substring(2, 9)}`);
  const [selectedAvatar, setSelectedAvatar] = useState<string>('Vera');
  const {
    connectionState,
    isRecording,
    activeVisual,
    connect,
    disconnect,
    sendVideoFrame,
    config
  } = useGeminiLive('google_1p', sessionId, selectedAvatar);

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

  // Cart & Order State
  const [cartItems, setCartItems] = useState<any[]>([]);
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [checkoutOrder, setCheckoutOrder] = useState<any | null>(null);
  const [aiFoundProducts, setAiFoundProducts] = useState<any[]>([]);

  useEffect(() => {
    if (products.length === 0) {
      fetch('/api/products?limit=24&offset=0')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setProducts(data);
        })
        .catch(err => console.error("Failed to load products in mobile view:", err));
    }
  }, [products.length]);

  // Handle Assistant Visual Tool Responses (Live Search & Cart synchronization)
  useEffect(() => {
    if (activeVisual?.toolName === 'search_products') {
      const items = (activeVisual.data as any)?.items || activeVisual.data || [];
      if (Array.isArray(items) && items.length > 0) {
        setAiFoundProducts(items);
        setSelectedCategory('All');
      }
    }
    if (activeVisual && ['add_to_cart', 'update_cart_item', 'remove_from_cart', 'get_cart'].includes(activeVisual.toolName || '')) {
      const items = (activeVisual.data as any)?.items || [];
      if (Array.isArray(items)) {
        setCartItems(items);
      }
      if (activeVisual.toolName === 'add_to_cart') {
        setIsCartOpen(true);
      }
    }
    if (activeVisual?.toolName === 'checkout_cart') {
      setCheckoutOrder(activeVisual.data);
      setCartItems([]);
      setIsCartOpen(false);
    }
    const productId = (activeVisual as any)?.arguments?.product_id;
    if (productId && ['get_product_details', 'get_product_reviews'].includes(activeVisual?.toolName || '')) {
      fetch(`/api/products/${productId}`)
        .then(res => res.json())
        .then(data => {
          if (data && data.product_id) setSelectedProduct(data);
        })
        .catch(err => console.error("Error fetching product details for mobile:", err));
    }
  }, [activeVisual]);

  // Sync initial cart
  useEffect(() => {
    executeMCPTool('get_cart', {}, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) {
          setCartItems(data.items);
        }
      })
      .catch(err => console.error('Failed to sync mobile cart:', err));
  }, [sessionId]);

  const categories = ['All', 'Electronics', 'Fashion', 'Home Decor', 'Appliances'];

  const displayedProducts = aiFoundProducts.length > 0 && selectedCategory === 'All'
    ? aiFoundProducts
    : selectedCategory === 'All'
    ? products
    : products.filter(p => (p.category || '').toLowerCase().includes(selectedCategory.toLowerCase()));

  const handleAddToCart = (e: React.MouseEvent, prod: any) => {
    if (e) e.stopPropagation();
    executeMCPTool('add_to_cart', { product_id: prod.product_id, quantity: 1 }, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) {
          setCartItems(data.items);
        } else {
          setCartItems(prev => [...prev, { ...prod, quantity: 1 }]);
        }
        setIsCartOpen(true);
      })
      .catch(err => {
        console.error('Failed to add to cart on mobile:', err);
        setCartItems(prev => [...prev, { ...prod, quantity: 1 }]);
        setIsCartOpen(true);
      });
  };

  const handleUpdateQty = (productId: string, quantity: number) => {
    executeMCPTool('update_cart_item', { product_id: productId, quantity }, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) setCartItems(data.items);
      })
      .catch(err => console.error('Failed to update qty on mobile:', err));
  };

  const handleRemoveItem = (productId: string) => {
    executeMCPTool('remove_from_cart', { product_id: productId }, 'google_1p', sessionId)
      .then((data: any) => {
        if (data && Array.isArray(data.items)) setCartItems(data.items);
      })
      .catch(err => console.error('Failed to remove item on mobile:', err));
  };

  const handleCheckout = () => {
    executeMCPTool('checkout_cart', {}, 'google_1p', sessionId)
      .then((data: any) => {
        setCheckoutOrder(data);
        setCartItems([]);
        setIsCartOpen(false);
      })
      .catch(err => console.error('Failed to checkout on mobile:', err));
  };

  const totalCartCount = cartItems.reduce((acc, item) => acc + (item.quantity || 1), 0);
  const totalCartPrice = cartItems.reduce((acc, item) => acc + ((Number(item.price) || 0) * (item.quantity || 1)), 0);

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      bgcolor: '#060913', 
      color: '#f8fafc', 
      py: { xs: 2, md: 4 }, 
      px: { xs: 1, md: 6 },
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      {/* Top Desktop Controls */}
      <Box sx={{ width: '100%', maxWidth: 1100, display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, px: 2 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: '900', letterSpacing: '-0.02em', background: 'linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #f472b6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            MULTIMODAL AI MOBILE EXPERIENCE
          </Typography>
          <Typography variant="caption" sx={{ color: '#94a3b8' }}>
            Real-time split-screen Voice & Video Shopping Concierge
          </Typography>
        </Box>
        <Button 
          variant="outlined" 
          startIcon={<ArrowBack />} 
          onClick={() => navigate('/')}
          sx={{ 
            color: '#ffffff', 
            borderColor: 'rgba(255,255,255,0.2)', 
            borderRadius: '24px',
            textTransform: 'none',
            px: 3,
            '&:hover': { borderColor: '#818cf8', bgcolor: 'rgba(129, 140, 248, 0.1)' }
          }}
        >
          Back to Desktop Store
        </Button>
      </Box>

      {/* Smartphone Device Simulator Casing */}
      <Box sx={{
        width: 395,
        height: 820,
        bgcolor: '#000000',
        borderRadius: '52px',
        p: '14px',
        boxShadow: '0 30px 80px rgba(0, 0, 0, 0.9), 0 0 50px rgba(129, 140, 248, 0.25)',
        border: '4px solid #1e293b',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Inner Phone Screen */}
        <Box sx={{
          flexGrow: 1,
          bgcolor: '#f8fafc',
          color: '#0f172a',
          borderRadius: '40px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative'
        }}>
          
          {/* Phone Status Bar */}
          <Box sx={{ 
            bgcolor: connectionState === 'connected' ? '#0b1120' : '#ffffff', 
            color: connectionState === 'connected' ? '#ffffff' : '#0f172a',
            pt: 1.5, 
            pb: 1, 
            px: 3, 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            fontSize: '12px',
            fontWeight: '800',
            transition: 'background-color 0.3s, color 0.3s',
            zIndex: 30
          }}>
            <Typography variant="caption" sx={{ fontWeight: '800' }}>9:41</Typography>
            {/* Dynamic Island with Live Wave indicator when speaking */}
            <Box sx={{ 
              width: connectionState === 'connected' ? 120 : 90, 
              height: 22, 
              bgcolor: '#000000', 
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 0.8,
              px: 1,
              transition: 'width 0.3s ease'
            }}>
              {connectionState === 'connected' && (
                <>
                  <Box sx={{ width: 6, height: 6, bgcolor: '#22c55e', borderRadius: '50%', boxShadow: '0 0 6px #22c55e' }} />
                  <Typography variant="caption" sx={{ color: '#ffffff', fontSize: '10px', fontWeight: '800', letterSpacing: '0.5px' }}>
                    {isRecording ? 'LIVE VOICE' : 'MUTED'}
                  </Typography>
                </>
              )}
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <SignalCellularAlt sx={{ fontSize: 14 }} />
              <Wifi sx={{ fontSize: 14 }} />
              <BatteryFull sx={{ fontSize: 14 }} />
            </Box>
          </Box>

          {/* AI Concierge Expandable Header / Split Screen Player */}
          <Box sx={{
            bgcolor: '#0b1120',
            color: '#ffffff',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
            display: 'flex',
            flexDirection: 'column',
            transition: 'all 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
            maxHeight: isAiExpanded ? 340 : 68,
            overflow: 'hidden',
            position: 'relative',
            zIndex: 20,
            boxShadow: isAiExpanded ? '0 8px 24px rgba(0,0,0,0.5)' : 'none'
          }}>
            {/* Top Bar of the AI Concierge */}
            <Box sx={{ 
              px: 2.5, 
              py: 1.2, 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              bgcolor: 'rgba(255,255,255,0.03)'
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AutoAwesome sx={{ fontSize: 18, color: '#818cf8' }} />
                <Typography variant="subtitle2" sx={{ fontWeight: '900', fontSize: '13px', letterSpacing: '-0.3px' }}>
                  {selectedAvatar} AI Concierge
                </Typography>
                {connectionState === 'connected' && (
                  <Chip 
                    size="small" 
                    label="LIVE" 
                    sx={{ height: 18, fontSize: '9px', fontWeight: '900', bgcolor: 'rgba(34, 197, 94, 0.2)', color: '#4ade80' }} 
                  />
                )}
              </Box>
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Select
                  size="small"
                  value={selectedAvatar}
                  disabled={connectionState !== 'disconnected'}
                  onChange={(e) => setSelectedAvatar(e.target.value)}
                  sx={{ 
                    height: 24, 
                    fontSize: '11px', 
                    fontWeight: 800, 
                    color: '#ffffff', 
                    bgcolor: 'rgba(255,255,255,0.1)',
                    borderRadius: '12px',
                    '& .MuiSvgIcon-root': { color: '#ffffff' },
                    '& .MuiOutlinedInput-notchedOutline': { border: 'none' }
                  }}
                >
                  <MenuItem value="Vera">Vera</MenuItem>
                  <MenuItem value="Kira">Kira</MenuItem>
                  <MenuItem value="Ingrid">Ingrid</MenuItem>
                  <MenuItem value="Sam">Sam</MenuItem>
                  <MenuItem value="Jay">Jay</MenuItem>
                  <MenuItem value="Kai">Kai</MenuItem>
                </Select>

                <IconButton 
                  size="small" 
                  onClick={() => setIsAiExpanded(!isAiExpanded)} 
                  sx={{ color: '#94a3b8', p: 0.5, '&:hover': { color: '#ffffff' } }}
                >
                  {isAiExpanded ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>
            </Box>

            {/* Expanded AI Avatar & Video Stream Screen */}
            {isAiExpanded && (
              <Box sx={{ 
                p: 1.5, 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                position: 'relative',
                flexGrow: 1,
                minHeight: 250
              }}>
                {/* Centered Portrait Box for 100% visible avatar */}
                <Box 
                  onClick={() => {
                    if (connectionState === 'disconnected') {
                      connect();
                    }
                  }}
                  sx={{ 
                    height: 210,
                    aspectRatio: '704 / 1280', 
                    borderRadius: 3, 
                    overflow: 'hidden', 
                    bgcolor: '#000000',
                    position: 'relative',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    cursor: connectionState === 'disconnected' ? 'pointer' : 'default'
                  }}
                >
                  <AvatarDisplay1P 
                    status={
                      connectionState === 'connected' ? 'ready' : 
                      connectionState === 'connecting' ? 'initializing' : 'idle'
                    } 
                    useVertexAI={config?.useVertexAI}
                    avatarName={selectedAvatar}
                  />

                  {/* Tap to start hint when idle */}
                  {connectionState === 'disconnected' && (
                    <Box sx={{
                      position: 'absolute',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 0.8,
                      color: '#ffffff',
                      textAlign: 'center',
                      pointerEvents: 'none'
                    }}>
                      <Box sx={{
                        width: 44,
                        height: 44,
                        borderRadius: '50%',
                        bgcolor: 'rgba(99, 102, 241, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: '2px solid rgba(165, 180, 252, 0.8)',
                        boxShadow: '0 0 14px rgba(99, 102, 241, 0.6)'
                      }}>
                        <GraphicEq sx={{ fontSize: 22, color: '#ffffff' }} />
                      </Box>
                      <Typography variant="caption" sx={{ fontWeight: 700, color: '#e2e8f0', fontSize: '11px' }}>
                        Tap to Talk to {selectedAvatar}
                      </Typography>
                    </Box>
                  )}

                  {/* Camera PiP inside the mobile avatar box */}
                  {isCameraActive && (
                    <Box sx={{
                      position: 'absolute',
                      bottom: 8,
                      right: 8,
                      width: 65,
                      height: 65,
                      borderRadius: '50%',
                      overflow: 'hidden',
                      border: '2px solid rgba(255,255,255,0.9)',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.6)',
                      zIndex: 15,
                      transform: 'scaleX(-1)',
                      bgcolor: '#000'
                    }}>
                      <video 
                        ref={cameraVideoRef}
                        autoPlay
                        playsInline
                        muted
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    </Box>
                  )}
                </Box>

                {/* Floating Action Controls under Avatar */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mt: 1.5 }}>
                  {connectionState !== 'connected' ? (
                    <Button 
                      variant="contained" 
                      size="small"
                      startIcon={connectionState === 'connecting' ? <CircularProgress size={14} color="inherit" /> : <PlayArrow />} 
                      onClick={connect}
                      disabled={connectionState === 'connecting'}
                      sx={{ 
                        bgcolor: '#6366f1', 
                        borderRadius: '20px', 
                        px: 3, 
                        py: 0.6,
                        fontSize: '12px',
                        fontWeight: '800', 
                        boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)',
                        '&:hover': { bgcolor: '#4f46e5' } 
                      }}
                    >
                      {connectionState === 'connecting' ? 'Connecting...' : 'Start Live Voice'}
                    </Button>
                  ) : (
                    <Button 
                      variant="contained" 
                      color="error"
                      size="small"
                      startIcon={<Stop />} 
                      onClick={disconnect}
                      sx={{ borderRadius: '20px', px: 2.5, py: 0.6, fontSize: '12px', fontWeight: '800' }}
                    >
                      End
                    </Button>
                  )}

                  {connectionState === 'connected' && (
                    <IconButton 
                      size="small"
                      onClick={isCameraActive ? stopCamera : startCamera}
                      sx={{ 
                        bgcolor: isCameraActive ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255,255,255,0.1)',
                        color: isCameraActive ? '#4ade80' : '#ffffff',
                        border: '1px solid rgba(255,255,255,0.15)',
                        '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' }
                      }}
                    >
                      {isCameraActive ? <Videocam fontSize="small" /> : <VideocamOff fontSize="small" />}
                    </IconButton>
                  )}
                </Box>
              </Box>
            )}
          </Box>

          {/* App Header (Product Search / Cart Bar) */}
          <Box sx={{ 
            bgcolor: '#ffffff', 
            px: 2.5, 
            py: 1.2, 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            borderBottom: '1px solid #e2e8f0',
            zIndex: 10
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: '900', letterSpacing: '-0.5px', color: '#0f172a' }}>
                {aiFoundProducts.length > 0 ? 'AI RECOMMENDED' : 'CATALOG'}
              </Typography>
              {aiFoundProducts.length > 0 && (
                <Chip 
                  size="small" 
                  label="Filtered by Assistant" 
                  onDelete={() => { setAiFoundProducts([]); setSelectedCategory('All'); }}
                  sx={{ height: 20, fontSize: '10px', fontWeight: '700', bgcolor: '#e0e7ff', color: '#4338ca' }}
                />
              )}
            </Box>
            <IconButton 
              size="small" 
              onClick={() => setIsCartOpen(true)}
              sx={{ bgcolor: '#000000', color: '#ffffff', '&:hover': { bgcolor: '#333333' } }}
            >
              <Badge badgeContent={totalCartCount} color="error">
                <ShoppingCart fontSize="small" />
              </Badge>
            </IconButton>
          </Box>

          {/* Category Filter Pills */}
          <Box sx={{ 
            display: 'flex', 
            gap: 1, 
            px: 2, 
            py: 1.2, 
            overflowX: 'auto', 
            bgcolor: '#ffffff',
            borderBottom: '1px solid #f1f5f9',
            '&::-webkit-scrollbar': { display: 'none' }
          }}>
            {categories.map((cat) => (
              <Chip
                key={cat}
                label={cat}
                size="small"
                onClick={() => { setSelectedCategory(cat); if(cat !== 'All') setAiFoundProducts([]); }}
                sx={{
                  fontWeight: '800',
                  fontSize: '11px',
                  bgcolor: selectedCategory === cat && aiFoundProducts.length === 0 ? '#000000' : '#f1f5f9',
                  color: selectedCategory === cat && aiFoundProducts.length === 0 ? '#ffffff' : '#475569',
                  '&:hover': { bgcolor: selectedCategory === cat && aiFoundProducts.length === 0 ? '#000000' : '#e2e8f0' }
                }}
              />
            ))}
          </Box>

          {/* Product Grid Area */}
          <Box sx={{ 
            flexGrow: 1, 
            overflowY: 'auto', 
            p: 2, 
            bgcolor: '#f8fafc', 
            pb: 9 
          }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.8 }}>
              {displayedProducts.map((prod) => (
                <Card 
                  key={prod.product_id}
                  onClick={() => setSelectedProduct(prod)}
                  sx={{ 
                    borderRadius: 3.5, 
                    boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                    border: '1px solid #f1f5f9',
                    cursor: 'pointer',
                    display: 'flex',
                    overflow: 'hidden',
                    bgcolor: '#ffffff',
                    transition: 'all 0.2s',
                    '&:active': { transform: 'scale(0.98)' }
                  }}
                >
                  <CardMedia
                    component="img"
                    sx={{ width: 110, objectFit: 'cover', bgcolor: '#f1f5f9' }}
                    image={prod.image_url || '/placeholder.png'}
                    alt={prod.name}
                  />
                  <CardContent sx={{ p: 1.5, flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: '800', lineHeight: 1.25, mb: 0.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', color: '#0f172a' }}>
                        {prod.name}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Star sx={{ fontSize: 14, color: '#f59e0b' }} />
                        <Typography variant="caption" sx={{ fontWeight: '800', color: '#64748b' }}>
                          {prod.rating ? Number(prod.rating).toFixed(1) : '4.8'}
                        </Typography>
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: '900', color: '#0f172a' }}>
                        ${prod.price ? Number(prod.price).toFixed(2) : '99.99'}
                      </Typography>
                      <IconButton 
                        size="small" 
                        onClick={(e) => handleAddToCart(e, prod)}
                        sx={{ bgcolor: '#0f172a', color: '#ffffff', '&:hover': { bgcolor: '#334155' } }}
                      >
                        <AddShoppingCart sx={{ fontSize: 16 }} />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              ))}

              {displayedProducts.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 6, color: '#94a3b8' }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: '700' }}>No products found.</Typography>
                  <Typography variant="caption">Try selecting another category or ask the assistant to search for items.</Typography>
                </Box>
              )}
            </Box>
          </Box>

          {/* Bottom App Navigation Bar */}
          <Box sx={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            bgcolor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(16px)',
            borderTop: '1px solid #e2e8f0',
            py: 1,
            px: 4,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            zIndex: 25
          }}>
            {[
              { label: 'Shop', icon: <Home /> },
              { 
                label: `${selectedAvatar} AI`, 
                icon: connectionState === 'connected' ? (
                  <Badge color="success" variant="dot">
                    <GraphicEq sx={{ color: '#22c55e' }} />
                  </Badge>
                ) : connectionState === 'connecting' ? (
                  <CircularProgress size={18} sx={{ color: '#6366f1' }} />
                ) : (
                  <GraphicEq />
                )
              },
              { label: 'Cart', icon: <Badge badgeContent={totalCartCount} color="error"><ShoppingCart /></Badge> },
              { label: 'Profile', icon: <Person /> }
            ].map((tab, idx) => (
              <Box 
                key={tab.label}
                onClick={() => {
                  setActiveBottomTab(idx);
                  if (idx === 1) {
                    setIsAiExpanded(true);
                    if (connectionState === 'disconnected') {
                      connect();
                    }
                  }
                  if (idx === 2) setIsCartOpen(true);
                }}
                sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'pointer', color: activeBottomTab === idx ? '#000000' : '#94a3b8' }}
              >
                {React.cloneElement(tab.icon, { sx: { fontSize: 22 } })}
                <Typography variant="caption" sx={{ fontSize: '10px', fontWeight: activeBottomTab === idx ? '800' : '600', mt: 0.2 }}>
                  {tab.label}
                </Typography>
              </Box>
            ))}
          </Box>

          {/* Mobile Cart Drawer (Bottom Sheet) */}
          <Drawer
            anchor="bottom"
            open={isCartOpen}
            onClose={() => setIsCartOpen(false)}
            slotProps={{
              paper: {
                sx: {
                  width: 395,
                  mx: 'auto',
                  borderTopLeftRadius: '28px',
                  borderTopRightRadius: '28px',
                  maxHeight: '75%',
                  bgcolor: '#ffffff',
                  color: '#0f172a',
                  p: 3,
                  display: 'flex',
                  flexDirection: 'column'
                }
              }
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: '900' }}>
                Your Cart ({totalCartCount})
              </Typography>
              <IconButton size="small" onClick={() => setIsCartOpen(false)}>
                <Close fontSize="small" />
              </IconButton>
            </Box>

            <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 3 }}>
              {cartItems.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: '#94a3b8' }}>
                  <ShoppingCart sx={{ fontSize: 40, mb: 1, opacity: 0.4 }} />
                  <Typography variant="body2" sx={{ fontWeight: '700' }}>Your cart is currently empty.</Typography>
                  <Typography variant="caption">Ask {selectedAvatar} to add an item while shopping!</Typography>
                </Box>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {cartItems.map((item, idx) => (
                    <Box key={`${item.product_id}_${idx}`} sx={{ display: 'flex', alignItems: 'center', gap: 2, pb: 2, borderBottom: '1px solid #f1f5f9' }}>
                      <img 
                        src={item.image_url || '/placeholder.png'} 
                        alt={item.name}
                        style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: '12px', background: '#f1f5f9' }} 
                      />
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: '800', lineHeight: 1.2 }}>
                          {item.name}
                        </Typography>
                        <Typography variant="caption" sx={{ fontWeight: '800', color: '#6366f1' }}>
                          ${Number(item.price || 0).toFixed(2)}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                          <IconButton size="small" onClick={() => handleUpdateQty(item.product_id, Math.max(1, (item.quantity || 1) - 1))} sx={{ p: 0.5, border: '1px solid #e2e8f0' }}>
                            <Remove sx={{ fontSize: 14 }} />
                          </IconButton>
                          <Typography variant="caption" sx={{ fontWeight: '800' }}>{item.quantity || 1}</Typography>
                          <IconButton size="small" onClick={() => handleUpdateQty(item.product_id, (item.quantity || 1) + 1)} sx={{ p: 0.5, border: '1px solid #e2e8f0' }}>
                            <Add sx={{ fontSize: 14 }} />
                          </IconButton>
                        </Box>
                      </Box>
                      <IconButton size="small" onClick={() => handleRemoveItem(item.product_id)} sx={{ color: '#ef4444' }}>
                        <Delete fontSize="small" />
                      </IconButton>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>

            {cartItems.length > 0 && (
              <Box sx={{ pt: 2, borderTop: '1px solid #e2e8f0' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: '800', color: '#64748b' }}>Total</Typography>
                  <Typography variant="h6" sx={{ fontWeight: '900', color: '#0f172a' }}>${totalCartPrice.toFixed(2)}</Typography>
                </Box>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleCheckout}
                  sx={{ bgcolor: '#0f172a', color: '#ffffff', py: 1.5, borderRadius: 3, fontWeight: '800', '&:hover': { bgcolor: '#334155' } }}
                >
                  Checkout with Assistant
                </Button>
              </Box>
            )}
          </Drawer>

          {/* Order Confirmation Modal */}
          <Dialog
            open={Boolean(checkoutOrder)}
            onClose={() => setCheckoutOrder(null)}
            slotProps={{
              paper: {
                sx: {
                  width: 340,
                  borderRadius: '28px',
                  p: 3,
                  textAlign: 'center',
                  bgcolor: '#ffffff',
                  color: '#0f172a'
                }
              }
            }}
          >
            <CheckCircle sx={{ fontSize: 56, color: '#22c55e', mx: 'auto', mb: 1.5 }} />
            <Typography variant="h6" sx={{ fontWeight: '900', mb: 1 }}>Order Confirmed!</Typography>
            <Typography variant="caption" sx={{ color: '#64748b', display: 'block', mb: 2 }}>
              Your order #{checkoutOrder?.order_id || 'AI-10928'} has been processed by {selectedAvatar}.
            </Typography>
            <Button
              fullWidth
              variant="contained"
              onClick={() => setCheckoutOrder(null)}
              sx={{ bgcolor: '#000000', color: '#ffffff', py: 1.2, borderRadius: 3, fontWeight: '800' }}
            >
              Continue Shopping
            </Button>
          </Dialog>

          {/* Product Detail Modal (Mobile Bottom Sheet) */}
          <Dialog
            open={Boolean(selectedProduct)}
            onClose={() => setSelectedProduct(null)}
            slotProps={{
              paper: {
                sx: {
                  width: 380,
                  borderRadius: '28px 28px 0 0',
                  position: 'absolute',
                  bottom: 0,
                  m: 0,
                  maxHeight: '80%',
                  bgcolor: '#ffffff',
                  color: '#0f172a',
                  p: 3,
                  display: 'flex',
                  flexDirection: 'column'
                }
              }
            }}
          >
            {selectedProduct && (
              <>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
                  <IconButton size="small" onClick={() => setSelectedProduct(null)}>
                    <Close fontSize="small" />
                  </IconButton>
                </Box>
                <Box sx={{ textAlign: 'center', mb: 2 }}>
                  <img 
                    src={selectedProduct.image_url || '/placeholder.png'} 
                    alt={selectedProduct.name}
                    style={{ width: '100%', maxHeight: 200, objectFit: 'contain', borderRadius: 16, background: '#f8fafc' }} 
                  />
                </Box>
                <Typography variant="h6" sx={{ fontWeight: '900', lineHeight: 1.2, mb: 1 }}>
                  {selectedProduct.name}
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: '900', color: '#6366f1', mb: 2 }}>
                  ${selectedProduct.price ? Number(selectedProduct.price).toFixed(2) : '99.99'}
                </Typography>
                <Typography variant="body2" sx={{ color: '#475569', lineHeight: 1.6, mb: 3, overflowY: 'auto', flexGrow: 1 }}>
                  {selectedProduct.description || 'No description available for this item.'}
                </Typography>
                <Button
                  fullWidth
                  variant="contained"
                  startIcon={<AddShoppingCart />}
                  onClick={(e) => {
                    handleAddToCart(e, selectedProduct);
                    setSelectedProduct(null);
                  }}
                  sx={{ bgcolor: '#000000', color: '#ffffff', py: 1.5, borderRadius: 3, fontWeight: '800', '&:hover': { bgcolor: '#333333' } }}
                >
                  Add to Mobile Cart
                </Button>
              </>
            )}
          </Dialog>

        </Box>
      </Box>
    </Box>
  );
}
