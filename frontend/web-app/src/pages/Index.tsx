import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, Heart, AlertCircle, Users } from 'lucide-react';

const Index = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="flex justify-center mb-6">
            <Activity className="h-20 w-20 text-blue-600" />
          </div>
          <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-4">
            HealSense
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
            AI-Powered Health Monitoring & Risk Prediction System
          </p>
          <div className="flex gap-4 justify-center">
            <Button size="lg" onClick={() => window.location.href = '/login'}>
              Sign In
            </Button>
            <Button size="lg" variant="outline" onClick={() => window.location.href = '/signup'}>
              Create Account
            </Button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
          <Card>
            <CardHeader>
              <Heart className="h-10 w-10 text-red-500 mb-2" />
              <CardTitle>Real-Time Monitoring</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Continuous tracking of 5 critical vital signs with instant updates
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Activity className="h-10 w-10 text-blue-500 mb-2" />
              <CardTitle>AI Predictions</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                LSTM deep learning model with 93%+ accuracy for health risk detection
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <AlertCircle className="h-10 w-10 text-yellow-500 mb-2" />
              <CardTitle>Smart Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Automatic notifications when vitals exceed safe thresholds
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <Users className="h-10 w-10 text-green-500 mb-2" />
              <CardTitle>Emergency System</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                One-tap access to emergency contacts with vital signs data
              </CardDescription>
            </CardContent>
          </Card>
        </div>

        {/* Stats */}
        <div className="mt-16 text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
            Proven Performance
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
            <div>
              <div className="text-4xl font-bold text-blue-600">93%+</div>
              <div className="text-gray-600 dark:text-gray-400 mt-2">Accuracy</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-green-600">96%+</div>
              <div className="text-gray-600 dark:text-gray-400 mt-2">Critical Recall</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-purple-600">&lt;5MB</div>
              <div className="text-gray-600 dark:text-gray-400 mt-2">Model Size</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-red-600">&lt;100ms</div>
              <div className="text-gray-600 dark:text-gray-400 mt-2">Inference Time</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
