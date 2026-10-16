const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/components/ai/AITransparencyPanel$': '<rootDir>/src/components/ai/AITransparencyPanel.tsx',
    '^@/components/layout/MobileBottomNav$': '<rootDir>/src/components/layout/MobileBottomNav.tsx',
    '^@/lib/command-palette$': '<rootDir>/src/lib/command-palette.ts',
    '^@/lib/api/scans$': '<rootDir>/src/lib/api/scans.ts',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
  ],
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)
