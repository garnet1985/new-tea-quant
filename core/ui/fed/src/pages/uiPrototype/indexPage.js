import React from 'react';
import { Navigate } from 'react-router-dom';
import { defaultCategoryPath } from './catalog';

/** `/dev/ui` 默认进入第一个大类。 */
function UiPrototypeIndexPage() {
  return <Navigate to={defaultCategoryPath()} replace />;
}

export default UiPrototypeIndexPage;
