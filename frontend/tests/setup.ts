import '@testing-library/jest-dom';

// Polyfill global fetch if not present in test environment
if (!globalThis.fetch) {
  // @ts-ignore
  globalThis.fetch = vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy', version: '0.1.0' }),
    })
  );
}
