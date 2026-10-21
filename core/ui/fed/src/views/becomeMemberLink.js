import React, { useEffect, useState } from 'react';
import { Button, Link } from '@mui/material';
import { fetchSiteUrls, resolveRegisterUrl } from '../api/siteApi';

/**
 * 官网注册入口（新标签页）。variant: link | button
 */
export default function BecomeMemberLink({
  variant = 'link',
  label = '成为会员',
  size = 'small',
  sx,
  className,
}) {
  const [href, setHref] = useState(resolveRegisterUrl(''));

  useEffect(() => {
    let alive = true;
    fetchSiteUrls()
      .then((urls) => {
        if (alive) setHref(resolveRegisterUrl(urls.registerUrl));
      })
      .catch(() => {
        if (alive) setHref(resolveRegisterUrl(''));
      });
    return () => {
      alive = false;
    };
  }, []);

  if (variant === 'button') {
    return (
      <Button
        component="a"
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        variant="outlined"
        size={size}
        className={className}
        sx={sx}
      >
        {label}
      </Button>
    );
  }

  return (
    <Link
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      underline="hover"
      className={className}
      sx={sx}
    >
      {label}
    </Link>
  );
}
