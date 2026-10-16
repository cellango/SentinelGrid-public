/** @jest-environment node */

import { POST } from '../route';

it('returns Gone without forwarding credentials to IAM', async () => {
  const fetchSpy = jest.spyOn(global, 'fetch').mockRejectedValue(new Error('Must not forward'));
  try {
    const response = await POST();
    expect(response.status).toBe(410);
    expect(await response.json()).toEqual({
      detail: expect.stringContaining('removed'),
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  } finally {
    fetchSpy.mockRestore();
  }
});
