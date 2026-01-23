'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * This page is deprecated.
 * Login functionality is now handled via LoginModal on the home page.
 * All requests to /login are redirected to the home page.
 */
export default function LoginPage() {
  const router = useRouter();
  
  useEffect(() => {
    // Redirect to home page - login is now handled via LoginModal
    router.replace('/');
  }, [router]);
  
  return null;
}
