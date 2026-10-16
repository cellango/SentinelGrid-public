// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'
const { seedTestAuth, silenceAuthLogs } = require('./src/test-utils/auth')
const {
  getMockPathname,
  getMockRouter,
  getMockSearchParams,
  resetNavigationMocks,
} = require('./src/test-utils/navigation')

// Seed a minimal auth/tenant context and reduce noisy auth logs during tests
seedTestAuth()
silenceAuthLogs()

beforeEach(() => {
  resetNavigationMocks()
})

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return getMockRouter()
  },
  useSearchParams() {
    return getMockSearchParams()
  },
  usePathname() {
    return getMockPathname()
  },
}))

// Mock next/link
jest.mock('next/link', () => {
  return ({ children, href, ...props }) => {
    return <a href={href} {...props}>{children}</a>
  }
})

// Mock react-hot-toast
jest.mock('react-hot-toast', () => ({
  default: {
    success: jest.fn(),
    error: jest.fn(),
    loading: jest.fn(),
  },
}))
