<script lang="ts">
  import { Input } from '$lib/components/ui/input';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Button } from '$lib/components/ui/button';
  import { Label } from '$lib/components/ui/label';
	import { page } from '$app/stores';

  let name = '';
  let description = '';
</script>

<h1 class="mt-10 text-center text-2xl font-semibold">Problem Definition</h1>
<form class="max-w-xl mx-auto flex flex-col gap-4" method="POST" action="?/create">
  <div>
    <Label for="name">Name</Label>
    <Input id="name" name="name" bind:value={name} required />
  </div>
  <div>
    <Label for="description">Description</Label>
    <Textarea id="description" name="description" bind:value={description} rows={3} />
  </div>
  <Button type="submit">Add Problem</Button>
</form>

{#if $page.form?.result}
  <p class="text-green-600">{JSON.stringify($page.form.result)}</p>
{/if}
{#if $page.form?.error}
  <p class="text-red-600">{$page.form.error}</p>
{/if}