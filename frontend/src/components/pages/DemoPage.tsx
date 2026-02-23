import React, { Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import LoadingIndicator from '../LoadingIndicator';
import { useAuth } from '../../hooks/useAuth';
import { useUploadModal } from '../layouts/AppLayout';

const DemoDashboard = React.lazy(() => import('../DemoDashboard'));

function DemoPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { openUploadModal } = useUploadModal();

  const handleExitToUpload = () => {
    const profile = process.env.REACT_APP_PROFILE || 'local';
    if (profile === 'local' || user) {
      openUploadModal();
    } else {
      navigate('/library');
    }
  };

  return (
    <Suspense
      fallback={
        <div className="app-container">
          <div className="app-loading">
            <LoadingIndicator size="lg" label="Loading..." />
          </div>
        </div>
      }
    >
      <DemoDashboard
        onClose={() => navigate('/')}
        onExitToUpload={handleExitToUpload}
      />
    </Suspense>
  );
}

export default DemoPage;
