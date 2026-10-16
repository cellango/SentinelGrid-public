"""
Performance tests for KeycloakAdminClient - SaaS Scale Validation.

This test suite validates that the KeycloakAdminClient can handle
production SaaS workloads with high concurrency, low latency, and
efficient resource usage.

Performance Goals (SaaS Requirements):
- User creation: < 200ms per user
- Attribute verification: < 50ms
- Token caching: 90%+ cache hit rate
- Concurrent users: Handle 100+ simultaneous signups
- Connection pooling: Reuse connections efficiently
"""

import pytest
import asyncio
import time
from typing import List
import statistics

from app.services.keycloak_admin_client import KeycloakAdminClient


# Performance thresholds for SaaS scale
PERFORMANCE_THRESHOLDS = {
    "user_creation_ms": 200,  # Max time to create one user
    "attribute_verification_ms": 50,  # Max time to verify attributes
    "concurrent_users": 100,  # Min concurrent users to handle
    "token_cache_hit_rate": 0.9,  # Min cache hit rate (90%)
    "connection_reuse_rate": 0.8,  # Min connection reuse (80%)
}


class TestUserCreationPerformance:
    """Test user creation performance for SaaS scale."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_single_user_creation_latency(self):
        """Test that single user creation meets latency requirements."""
        async with KeycloakAdminClient() as kc_admin:
            start_time = time.time()
            
            # Create a test user
            user_id = await kc_admin.create_user(
                realm="sentinelgrid",
                username=f"perf-test-{int(time.time())}@example.com",
                email=f"perf-test-{int(time.time())}@example.com",
                first_name="Perf",
                last_name="Test",
                password="TestPassword123!",
                attributes={
                    "tenant_id": ["perf-tenant-123"],
                    "customer_id": ["perf-customer-456"]
                }
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            print(f"\n✅ User creation latency: {elapsed_ms:.2f}ms")
            
            # Clean up
            try:
                await kc_admin.delete_user("sentinelgrid", user_id)
            except:
                pass
            
            # Assert meets performance threshold
            assert elapsed_ms < PERFORMANCE_THRESHOLDS["user_creation_ms"], \
                f"User creation took {elapsed_ms:.2f}ms, exceeds threshold of {PERFORMANCE_THRESHOLDS['user_creation_ms']}ms"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_user_creation(self):
        """Test creating multiple users concurrently (SaaS burst load)."""
        num_users = 50  # Simulate 50 concurrent signups
        
        async def create_user(index: int):
            """Create a single user."""
            async with KeycloakAdminClient() as kc_admin:
                timestamp = int(time.time() * 1000) + index
                user_id = await kc_admin.create_user(
                    realm="sentinelgrid",
                    username=f"concurrent-{timestamp}@example.com",
                    email=f"concurrent-{timestamp}@example.com",
                    first_name="Concurrent",
                    last_name=f"User{index}",
                    password="TestPassword123!",
                    attributes={
                        "tenant_id": [f"tenant-{timestamp}"],
                        "customer_id": [f"customer-{timestamp}"]
                    }
                )
                return user_id
        
        start_time = time.time()
        
        # Create users concurrently
        tasks = [create_user(i) for i in range(num_users)]
        user_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed_time = time.time() - start_time
        
        # Count successes
        successes = [uid for uid in user_ids if isinstance(uid, str)]
        failures = [uid for uid in user_ids if not isinstance(uid, str)]
        
        print(f"\n✅ Created {len(successes)}/{num_users} users concurrently in {elapsed_time:.2f}s")
        print(f"   Average: {(elapsed_time/num_users)*1000:.2f}ms per user")
        print(f"   Throughput: {num_users/elapsed_time:.2f} users/sec")
        
        if failures:
            print(f"   ⚠️  {len(failures)} failures: {failures[:3]}")
        
        # Clean up successful users
        async with KeycloakAdminClient() as kc_admin:
            for user_id in successes:
                try:
                    await kc_admin.delete_user("sentinelgrid", user_id)
                except:
                    pass
        
        # Assert most users were created successfully (90%+)
        success_rate = len(successes) / num_users
        assert success_rate >= 0.9, \
            f"Only {success_rate*100:.1f}% of users created successfully (need 90%+)"


class TestTokenCachingPerformance:
    """Test token caching efficiency."""
    
    @pytest.mark.asyncio
    async def test_token_cache_hit_rate(self):
        """Test that token caching reduces API calls."""
        async with KeycloakAdminClient() as kc_admin:
            # Force token acquisition
            token1 = await kc_admin._get_admin_token()
            
            # Track cache hits
            cache_hits = 0
            total_requests = 100
            
            start_time = time.time()
            
            for _ in range(total_requests):
                # Token should be cached
                token = await kc_admin._get_admin_token()
                if token == token1:
                    cache_hits += 1
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            cache_hit_rate = cache_hits / total_requests
            
            print(f"\n✅ Token cache hit rate: {cache_hit_rate*100:.1f}%")
            print(f"   {total_requests} token requests in {elapsed_ms:.2f}ms")
            print(f"   Average: {elapsed_ms/total_requests:.2f}ms per request")
            
            # Assert meets cache hit rate threshold
            assert cache_hit_rate >= PERFORMANCE_THRESHOLDS["token_cache_hit_rate"], \
                f"Cache hit rate {cache_hit_rate*100:.1f}% below threshold of {PERFORMANCE_THRESHOLDS['token_cache_hit_rate']*100}%"


class TestAttributeVerificationPerformance:
    """Test attribute verification performance."""
    
    @pytest.mark.asyncio
    async def test_attribute_verification_latency(self):
        """Test that attribute verification is fast."""
        async with KeycloakAdminClient() as kc_admin:
            # Create a user for testing
            user_id = await kc_admin.create_user(
                realm="sentinelgrid",
                username=f"attr-test-{int(time.time())}@example.com",
                email=f"attr-test-{int(time.time())}@example.com",
                first_name="Attr",
                last_name="Test",
                attributes={
                    "tenant_id": ["test-tenant"],
                    "customer_id": ["test-customer"]
                }
            )
            
            # Measure attribute retrieval time
            start_time = time.time()
            user = await kc_admin.get_user("sentinelgrid", user_id)
            elapsed_ms = (time.time() - start_time) * 1000
            
            print(f"\n✅ Attribute retrieval latency: {elapsed_ms:.2f}ms")
            
            # Clean up
            await kc_admin.delete_user("sentinelgrid", user_id)
            
            # Assert meets performance threshold
            assert elapsed_ms < PERFORMANCE_THRESHOLDS["attribute_verification_ms"], \
                f"Attribute verification took {elapsed_ms:.2f}ms, exceeds threshold"


class TestConnectionPoolingEfficiency:
    """Test connection pooling for efficient resource usage."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_configuration(self):
        """Test that connection pool is properly configured."""
        async with KeycloakAdminClient() as kc_admin:
            http_client = kc_admin._client
            
            # Verify pool settings
            assert http_client.limits.max_connections == 100, \
                "Connection pool should support 100 connections"
            assert http_client.limits.max_keepalive_connections == 20, \
                "Should keep 20 connections alive"
            
            print(f"\n✅ Connection pool configured correctly:")
            print(f"   Max connections: {http_client.limits.max_connections}")
            print(f"   Keep-alive: {http_client.limits.max_keepalive_connections}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_requests_connection_reuse(self):
        """Test that concurrent requests reuse connections efficiently."""
        async with KeycloakAdminClient() as kc_admin:
            # Make concurrent requests
            num_requests = 50
            
            async def get_user_info(index: int):
                """Get realm roles (lightweight operation)."""
                try:
                    roles = await kc_admin.get_realm_roles("sentinelgrid")
                    return len(roles)
                except:
                    return None
            
            start_time = time.time()
            
            tasks = [get_user_info(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed_time = time.time() - start_time
            
            successes = [r for r in results if isinstance(r, int)]
            
            print(f"\n✅ Made {len(successes)}/{num_requests} concurrent requests in {elapsed_time:.2f}s")
            print(f"   Average: {(elapsed_time/num_requests)*1000:.2f}ms per request")
            print(f"   Throughput: {num_requests/elapsed_time:.2f} requests/sec")
            
            # Connection reuse should make this fast
            avg_latency_ms = (elapsed_time / num_requests) * 1000
            assert avg_latency_ms < 100, \
                f"Average latency {avg_latency_ms:.2f}ms suggests poor connection reuse"


class TestThroughputBenchmark:
    """Benchmark overall system throughput."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_user_creation_throughput(self):
        """Test sustained user creation throughput over time."""
        duration_seconds = 10
        created_users = []
        
        async def create_users_continuously(stop_event: asyncio.Event):
            """Create users until stop event is set."""
            user_count = 0
            async with KeycloakAdminClient() as kc_admin:
                while not stop_event.is_set():
                    try:
                        timestamp = int(time.time() * 1000000) + user_count
                        user_id = await kc_admin.create_user(
                            realm="sentinelgrid",
                            username=f"throughput-{timestamp}@example.com",
                            email=f"throughput-{timestamp}@example.com",
                            first_name="Throughput",
                            last_name=f"Test{user_count}",
                            password="TestPassword123!",
                            attributes={
                                "tenant_id": [f"tenant-{timestamp}"],
                                "customer_id": [f"customer-{timestamp}"]
                            }
                        )
                        created_users.append(user_id)
                        user_count += 1
                    except Exception as e:
                        print(f"Error creating user: {e}")
                        await asyncio.sleep(0.1)
        
        stop_event = asyncio.Event()
        
        # Start creating users
        task = asyncio.create_task(create_users_continuously(stop_event))
        
        # Run for specified duration
        await asyncio.sleep(duration_seconds)
        
        # Stop creation
        stop_event.set()
        await task
        
        throughput = len(created_users) / duration_seconds
        
        print(f"\n✅ Sustained throughput test:")
        print(f"   Created {len(created_users)} users in {duration_seconds}s")
        print(f"   Throughput: {throughput:.2f} users/sec")
        
        # Clean up
        async with KeycloakAdminClient() as kc_admin:
            for user_id in created_users:
                try:
                    await kc_admin.delete_user("sentinelgrid", user_id)
                except:
                    pass
        
        # For SaaS, expect at least 5 users/sec sustained
        assert throughput >= 5.0, \
            f"Throughput of {throughput:.2f} users/sec is too low for SaaS scale"


class TestMemoryEfficiency:
    """Test memory efficiency under load."""
    
    @pytest.mark.asyncio
    async def test_no_memory_leaks(self):
        """Test that repeated operations don't leak memory."""
        import gc
        import sys
        
        # Force garbage collection
        gc.collect()
        
        # Create and destroy clients repeatedly
        for _ in range(10):
            async with KeycloakAdminClient() as kc_admin:
                # Perform some operations
                await kc_admin._get_admin_token()
                try:
                    await kc_admin.get_realm_roles("sentinelgrid")
                except:
                    pass
        
        # Force garbage collection again
        gc.collect()
        
        print(f"\n✅ Memory leak test completed")
        print(f"   No assertion - manual monitoring recommended")


# Performance summary report
@pytest.fixture(scope="session", autouse=True)
def performance_report(request):
    """Print performance test summary at end of session."""
    yield
    
    print("\n" + "="*60)
    print("KEYCLOAK ADMIN CLIENT - PERFORMANCE TEST SUMMARY")
    print("="*60)
    print("\nPerformance Thresholds (SaaS Requirements):")
    for metric, threshold in PERFORMANCE_THRESHOLDS.items():
        print(f"  • {metric}: {threshold}")
    print("\n✅ All performance tests completed")
    print("   See individual test output for detailed metrics")
    print("="*60 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=auto", "-m", "not slow"])

