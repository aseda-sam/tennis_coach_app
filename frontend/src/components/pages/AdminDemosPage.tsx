import React, { Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import LoadingIndicator from '../LoadingIndicator';

const AdminDemoManagement = React.lazy(() => import('../AdminDemoManagement'));

function AdminDemosPage() {
  const navigate = useNavigate();

  return (
    <div className="app-container">
      <Suspense
        fallback={
          <div className="app-loading">
            <LoadingIndicator size="lg" label="Loading..." />
          </div>
        }
      >
        <AdminDemoManagement
          onOpenVideo={(video) => navigate(`/videos/${video.id}`)}
          onNavigateToDemo={() => navigate('/demo')}
        />
      </Suspense>
    </div>
  );
}

export default AdminDemosPage;
