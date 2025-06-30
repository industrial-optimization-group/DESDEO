<script lang="ts">
	import { methodSelection } from '../../../stores/methodSelection';
	import * as Menubar from '$lib/components/ui/menubar/index.js';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
</script>

<Resizable.PaneGroup direction="vertical">
	<Resizable.Pane class="p-2">
		<div class="flex-row">
			<div class="flex flex-row items-center justify-between gap-4">
				<div class="font-semibold">Alternatives</div>
				<Menubar.Root>
					<Menubar.Menu>
						<Menubar.Trigger>View</Menubar.Trigger>
						<Menubar.Content>
							<Menubar.Item>
								Current iteration<Menubar.Shortcut>⌘T</Menubar.Shortcut>
							</Menubar.Item>
							<Menubar.Item>
								Best candidates <Menubar.Shortcut>⌘N</Menubar.Shortcut>
							</Menubar.Item>
							<Menubar.Item>All solutions</Menubar.Item>
						</Menubar.Content>
					</Menubar.Menu>
					<Menubar.Menu>
						<Menubar.Trigger>Plot</Menubar.Trigger>
						<Menubar.Content>
							<Menubar.Item>
								Parallel coordinates <Menubar.Shortcut>⌘Z</Menubar.Shortcut>
							</Menubar.Item>
							<Menubar.Item>
								Bar charts <Menubar.Shortcut>⇧⌘Z</Menubar.Shortcut>
							</Menubar.Item>

							<Menubar.Item>Petal diagram</Menubar.Item>
							<Menubar.Item>Spider chart</Menubar.Item>
							<Menubar.Item>Scatter plot</Menubar.Item>
						</Menubar.Content>
					</Menubar.Menu>
					<Menubar.Menu>
						<Menubar.Trigger>Save</Menubar.Trigger>
						<Menubar.Content>
							<Menubar.Separator />
							<Menubar.Item inset>
								Reload <Menubar.Shortcut>⌘R</Menubar.Shortcut>
							</Menubar.Item>
							<Menubar.Item inset>
								Force Reload <Menubar.Shortcut>⇧⌘R</Menubar.Shortcut>
							</Menubar.Item>
							<Menubar.Separator />
							<Menubar.Item inset>Toggle Fullscreen</Menubar.Item>
							<Menubar.Separator />
							<Menubar.Item inset>Hide Sidebar</Menubar.Item>
						</Menubar.Content>
					</Menubar.Menu>
				</Menubar.Root>
			</div>

			<div class="h-full w-full">
				<!-- Desktop: two columns, Mobile: two rows -->
				<div class="grid h-full w-full gap-4 xl:grid-cols-1">
					<div class="min-h-[50rem] flex-1 rounded bg-gray-100 p-4">
						<!-- First column/row content -->
						<span>Visualization</span>
					</div>
					<!-- 					<div class="flex-1 bg-gray-200 rounded p-4 min-h-[150px]">
	
						<span>Numerical values</span>
					</div> -->
				</div>
			</div>
		</div>
	</Resizable.Pane>
	<Resizable.Handle />
	<Resizable.Pane class="p-2">
		<span>Best candidates</span>
	</Resizable.Pane>
</Resizable.PaneGroup>
