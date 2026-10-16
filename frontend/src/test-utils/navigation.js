const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
};

let currentSearchParams = new URLSearchParams();
let currentPathname = '/';

function resetNavigationMocks() {
  mockRouter.push.mockReset();
  mockRouter.replace.mockReset();
  mockRouter.prefetch.mockReset();
  mockRouter.back.mockReset();
  currentSearchParams = new URLSearchParams();
  currentPathname = '/';
}

function mockNextRouter(overrides = {}) {
  Object.assign(mockRouter, overrides);
  return mockRouter;
}

function mockSearchParams(params = {}) {
  const nextParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      nextParams.set(key, String(value));
    }
  });
  currentSearchParams = nextParams;
  return currentSearchParams;
}

function mockPathname(pathname = '/') {
  currentPathname = pathname;
  return currentPathname;
}

function getMockRouter() {
  return mockRouter;
}

function getMockSearchParams() {
  return currentSearchParams;
}

function getMockPathname() {
  return currentPathname;
}

module.exports = {
  getMockPathname,
  getMockRouter,
  getMockSearchParams,
  mockNextRouter,
  mockPathname,
  mockSearchParams,
  resetNavigationMocks,
};
