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

import { CardMedia, Typography, Box, Button, Rating } from '@mui/material';

interface ProductCardProps {
  item: {
    product_id: string;
    name: string;
    description: string;
    price: string;
    image_url: string;
    rating?: number;
    reviews_count?: number;
  };
  onAddToCart?: (productId: string) => void;
  onProductClick?: (product: any) => void;
}

export function ProductCard({ item, onAddToCart, onProductClick }: ProductCardProps) {
  return (
    <Box 
      onClick={() => onProductClick && onProductClick(item)}
      sx={{
        borderRadius: 5,
        border: '1px solid #e2e8f0',
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'transform 0.2s, box-shadow 0.2s',
        bgcolor: '#ffffff',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 12px 24px rgba(0,0,0,0.06)',
          borderColor: 'primary.main'
        },
        display: 'flex',
        flexDirection: 'column',
        height: 290,
        boxSizing: 'border-box'
      }}
    >
      {item.image_url && (
        <CardMedia
          component="img"
          height="140"
          image={item.image_url}
          alt={item.name}
          sx={{ objectFit: 'cover' }}
        />
      )}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', p: 2, minHeight: 0 }}>
        <Box>
          <Typography 
            variant="subtitle2" 
            sx={{ 
              fontWeight: 'bold', 
              textAlign: 'left', 
              display: '-webkit-box', 
              WebkitLineClamp: 2, 
              WebkitBoxOrient: 'vertical', 
              overflow: 'hidden',
              fontSize: '0.85rem',
              lineHeight: 1.2
            }}
          >
            {item.name}
          </Typography>
          
          {item.rating !== undefined && item.reviews_count !== undefined && item.reviews_count > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
              <Rating 
                name="read-only-rating" 
                value={item.rating} 
                precision={0.1} 
                readOnly 
                size="small"
                sx={{ fontSize: '0.9rem' }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                ({item.reviews_count})
              </Typography>
            </Box>
          )}
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
          <Typography variant="h6" color="primary" sx={{ fontWeight: '800', textAlign: 'left', fontSize: '1.05rem' }}>
            ${item.price}
          </Typography>
          {onAddToCart && (
            <Button
              variant="contained"
              size="small"
              onClick={(e) => {
                e.stopPropagation(); // Prevent card click / product detail opening
                onAddToCart(item.product_id);
              }}
              sx={{ 
                borderRadius: '12px', 
                textTransform: 'none', 
                fontWeight: 'bold',
                fontSize: '0.75rem',
                py: 0.5,
                px: 1.5
              }}
            >
              Buy
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
}
