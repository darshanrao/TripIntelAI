import { useState, useEffect, useRef } from 'react';
import Head from 'next/head';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/router';

export default function LandingPage() {
  const router = useRouter();
  const [scrollY, setScrollY] = useState(0);
  const heroRef = useRef(null);
  const featureRefs = [useRef(null), useRef(null), useRef(null)];
  
  const handleStartNow = () => {
    router.push('/chat');
  };

  // Force scroll to top when component mounts
  useEffect(() => {
    // Clear hash fragment from URL if present
    if (window.location.hash) {
      // Push the current path without the hash
      router.replace(router.pathname);
    }
    
    // This ensures we start at the top of the page
    window.scrollTo(0, 0);
    document.body.scrollTop = 0;
    document.documentElement.scrollTop = 0;
    
    // Also listen for router events to handle client-side navigation
    const handleRouteChange = () => {
      window.scrollTo(0, 0);
    };

    router.events.on('routeChangeComplete', handleRouteChange);
    
    return () => {
      router.events.off('routeChangeComplete', handleRouteChange);
    };
  }, [router]);

  // Handle scroll position tracking
  useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);
    };
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Handle anchor links to prevent default behavior
  useEffect(() => {
    const handleAnchorClick = (e) => {
      const href = e.currentTarget.getAttribute('href');
      if (href && href.startsWith('#')) {
        e.preventDefault();
        const element = document.getElementById(href.substring(1));
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
      }
    };

    const anchors = document.querySelectorAll('a[href^="#"]');
    anchors.forEach(anchor => {
      anchor.addEventListener('click', handleAnchorClick);
    });

    return () => {
      anchors.forEach(anchor => {
        anchor.removeEventListener('click', handleAnchorClick);
      });
    };
  }, []);

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Head>
        <title>TripIntel | Intelligent Travel Planning</title>
        <meta name="description" content="Plan your perfect trip with AI assistance" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100 py-4 px-6">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="text-xl font-semibold text-black">TripIntel</div>
          <div className="flex space-x-8">
            <a href="#home" className="text-gray-600 hover:text-black transition-colors">Home</a>
            <a href="#features" className="text-gray-600 hover:text-black transition-colors">Features</a>
            <a href="#how-it-works" className="text-gray-600 hover:text-black transition-colors">How It Works</a>
            <button 
              onClick={handleStartNow}
              className="px-5 py-1.5 rounded-full bg-black text-white hover:bg-gray-900 transition-colors"
            >
              Start Now
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 relative overflow-hidden" ref={heroRef} id="home">
        <div className="max-w-6xl mx-auto relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="text-center mb-16"
          >
            <h1 className="text-6xl font-bold tracking-tight mb-6">
              TripIntel
            </h1>
            <p className="text-2xl text-gray-500 max-w-3xl mx-auto">
              Built for intelligent travel planning.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
            >
              <h2 className="text-4xl font-semibold mb-6">
                Plan your perfect trip with AI
              </h2>
              <p className="text-xl text-gray-500 mb-8 leading-relaxed">
                TripIntel uses advanced AI to help you create personalized itineraries, find the best flights, and discover hidden gems at your destination — all through natural conversation.
              </p>
              <motion.button 
                onClick={handleStartNow}
                className="px-8 py-3 bg-black text-white rounded-full text-lg font-medium hover:bg-gray-800 transition-all"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
              >
                Start planning now
              </motion.button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
              className="rounded-2xl overflow-hidden relative flex items-center justify-center bg-transparent"
            >
              <img 
                src="/static/Plane Airplane Sticker by worldshop.eu" 
                alt="Travel Animation" 
                className="w-1/2 h-auto object-contain" 
                style={{ filter: 'none', boxShadow: 'none', background: 'transparent' }}
              />
            </motion.div>
          </div>
        </div>

        {/* Background gradient elements */}
        <div className="absolute top-0 left-1/4 w-80 h-80 bg-blue-100 rounded-full filter blur-3xl opacity-20 -z-10"></div>
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-purple-100 rounded-full filter blur-3xl opacity-20 -z-10"></div>
      </section>

      {/* Features Intro */}
      <section id="features" className="py-24 px-6 bg-gray-50 text-center">
        <motion.div 
          className="max-w-4xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="text-5xl font-semibold mb-6">
            Hours of Planning<br />
            <span className="text-gray-400">Done in Minutes</span>
          </h2>
          <p className="text-xl text-gray-500 mt-6 mb-16">
            Our AI assistant transforms travel planning from tedious to effortless.
          </p>
        </motion.div>
      </section>

      {/* Features Detailed */}
      <section className="py-16 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Feature 1 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center min-h-[80vh] py-16" ref={featureRefs[0]}>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8 }}
            >
              <div className="text-sm uppercase tracking-wider text-gray-400 mb-3">Natural conversation</div>
              <h3 className="text-4xl font-semibold mb-5">Plan your trip with simple chat</h3>
              <p className="text-xl text-gray-500 leading-relaxed mb-6">
                Just tell our AI what kind of trip you want, and it will handle all the details. No more juggling between dozens of travel sites and apps.
              </p>
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="p-6 rounded-2xl"
            >
              <div className="bg-white rounded-xl p-6 shadow-sm">
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white text-xs font-medium">
                    U
                  </div>
                  <div className="flex-1">
                    <p className="text-gray-800">I want to plan a 5-day trip to Tokyo in March for two people who love food and culture.</p>
                  </div>
                </div>
              </div>
              <div className="mt-4 bg-gray-50 rounded-xl p-6 shadow-sm">
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center text-white text-xs font-medium">
                    TI
                  </div>
                  <div className="flex-1">
                    <p className="text-gray-800">I'll create a 5-day Tokyo itinerary focused on food and culture experiences! Would you prefer budget, mid-range, or luxury accommodations?</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
          
          {/* Feature 2 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center min-h-[80vh] py-16" ref={featureRefs[1]}>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="p-6 rounded-2xl order-2 md:order-1 relative flex items-center justify-center bg-transparent"
            >
              <img 
                src="/static/Plane Airplane Sticker by worldshop.eu" 
                alt="Itinerary View" 
                className="w-1/2 h-auto object-contain" 
                style={{ filter: 'none', boxShadow: 'none', background: 'transparent' }}
              />
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8 }}
              className="order-1 md:order-2"
            >
              <div className="text-sm uppercase tracking-wider text-gray-400 mb-3">Smart itineraries</div>
              <h3 className="text-4xl font-semibold mb-5">Get detailed daily plans</h3>
              <p className="text-xl text-gray-500 leading-relaxed mb-6">
                Our AI generates comprehensive day-by-day itineraries with attractions, dining options, and transit information — all optimized for efficiency and your preferences.
              </p>
            </motion.div>
          </div>
          
          {/* Feature 3 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center min-h-[80vh] py-16" ref={featureRefs[2]}>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8 }}
            >
              <div className="text-sm uppercase tracking-wider text-gray-400 mb-3">Flight selection</div>
              <h3 className="text-4xl font-semibold mb-5">Find the perfect flights</h3>
              <p className="text-xl text-gray-500 leading-relaxed mb-6">
                Our AI assistant helps you compare and select flights based on your preferences for price, schedule, and airline — presenting only the most relevant options.
              </p>
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="p-6 rounded-2xl flex items-center justify-center bg-transparent"
            >
              <img 
                src="/static/Plane Airplane Sticker by worldshop.eu" 
                alt="Flight Selection" 
                className="w-1/2 h-auto object-contain" 
                style={{ filter: 'none', boxShadow: 'none', background: 'transparent' }}
              />
            </motion.div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-24 px-6 bg-black text-white">
        <motion.div 
          className="max-w-6xl mx-auto"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="text-5xl font-semibold text-center mb-20">
            How it works
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <motion.div 
              className="flex flex-col items-center text-center"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-black text-xl font-semibold mb-8">1</div>
              <h3 className="text-2xl font-semibold mb-4">Tell us your plans</h3>
              <p className="text-gray-300">
                Share your destination, dates, preferences, and any specific requirements in a natural conversation.
              </p>
            </motion.div>
            
            <motion.div 
              className="flex flex-col items-center text-center"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-black text-xl font-semibold mb-8">2</div>
              <h3 className="text-2xl font-semibold mb-4">Review options</h3>
              <p className="text-gray-300">
                Browse through flight options, accommodation suggestions, and activity recommendations.
              </p>
            </motion.div>
            
            <motion.div 
              className="flex flex-col items-center text-center"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-black text-xl font-semibold mb-8">3</div>
              <h3 className="text-2xl font-semibold mb-4">Get your itinerary</h3>
              <p className="text-gray-300">
                Receive a complete day-by-day travel plan with all the details you need for a perfect trip.
              </p>
            </motion.div>
          </div>
        </motion.div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-6 text-center relative overflow-hidden">
        <motion.div 
          className="max-w-3xl mx-auto relative z-10"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="text-5xl font-semibold mb-8">
            Ready to plan your next adventure?
          </h2>
          <p className="text-xl text-gray-500 mb-12">
            Start creating your perfect travel plan today.
          </p>
          <motion.button 
            onClick={handleStartNow}
            className="px-8 py-4 bg-black text-white rounded-full text-xl font-medium hover:bg-gray-800 transition-all"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
          >
            Try TripIntel now
          </motion.button>
        </motion.div>

        {/* Background gradient elements */}
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-blue-50 rounded-full filter blur-3xl opacity-30 -z-10"></div>
        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-purple-50 rounded-full filter blur-3xl opacity-30 -z-10"></div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8 px-6 bg-white">
        <div className="max-w-6xl mx-auto flex justify-center items-center">
          <div className="text-lg font-semibold text-black">TripIntel</div>
        </div>
      </footer>
    </div>
  );
} 