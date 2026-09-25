#nullable enable
using System;
using T3.Core.DataTypes;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Interfaces;
using T3.Core.Operator.Slots;

namespace PrismalLabs.BlenderExport;

/// <summary>Warms every Blender world while paused before the world switch can play.</summary>
[Guid("f3cf6968-ad60-41e4-a900-32566c8f0f2d")]
public sealed class BlenderWorldPreload : Instance<BlenderWorldPreload>, IStatusProvider
{
    [Input(Guid = "ebcd2d78-2b80-4b36-bd74-d074868b86dc")]
    public readonly MultiInputSlot<SceneSetup> Worlds = new();

    [Input(Guid = "8bf57a9c-25a2-4a41-a349-4a1769ff904b")]
    public readonly InputSlot<Command> Command = new();

    [Output(Guid = "507e7775-3442-4271-a7fe-6cfa86462e22", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<Command> Output = new();

    private bool _warmed;
    private int _worldCount;
    private int _missingCount;

    public BlenderWorldPreload() => Output.UpdateAction = Update;

    private void Update(EvaluationContext context)
    {
        // The editor evaluates its output while paused immediately after opening
        // a project. Pulling every scene setup here loads glTF meshes, textures,
        // and animation bindings before transport starts. Recheck on later
        // paused evaluations so edits to an inactive world are warmed too.
        var paused = Math.Abs(context.Playback.PlaybackSpeed) <= 0.001;
        if (paused)
        {
            var worlds = Worlds.GetCollectedTypedInputs();
            _worldCount = worlds.Count;
            _missingCount = 0;
            foreach (var world in worlds)
            {
                if (world.GetValue(context) == null)
                    _missingCount++;
            }
            _warmed = _worldCount > 0 && _missingCount == 0;
        }
        // A project opened with transport already running cannot initialize
        // any world on that playback frame.
        else if (!_warmed)
            return;

        Command.GetValue(context);
    }

    IStatusProvider.StatusLevel IStatusProvider.GetStatusLevel()
        => !_warmed || _missingCount > 0
               ? IStatusProvider.StatusLevel.Warning
               : IStatusProvider.StatusLevel.Success;

    string IStatusProvider.GetStatusMessage()
        => !_warmed ? "Pause playback to preload Blender worlds before rendering."
           : _missingCount > 0 ? $"Preloaded {_worldCount - _missingCount} of {_worldCount} Blender world branches."
           : $"Preloaded {_worldCount} Blender world branches before playback.";
}
