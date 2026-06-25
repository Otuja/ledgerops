import { useState, useEffect, useRef } from 'react';

export function usePolling(fetchFunc, intervalMs = 10000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const savedCallback = useRef(fetchFunc);

  useEffect(() => {
    savedCallback.current = fetchFunc;
  }, [fetchFunc]);

  useEffect(() => {
    let isMounted = true;
    let timerId = null;

    const tick = async () => {
      try {
        const result = await savedCallback.current();
        if (isMounted) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
          timerId = setTimeout(tick, intervalMs);
        }
      }
    };

    tick();

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [intervalMs]);

  return { data, loading, error };
}
