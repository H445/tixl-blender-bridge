#nullable enable
using System;
using SharpDX.Direct3D11;
using T3.Core.DataTypes;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Slots;

namespace PrismalLabs.BlenderExport;

/// <summary>Exposes the four material maps of an animated glTF primitive as TiXL textures.</summary>
[Guid("b1dc33bf-f973-5822-b079-e7ed36bb3ab1")]
public sealed class BlenderTextureSelect : Instance<BlenderTextureSelect>
{
    [Input(Guid = "ca9a3db9-6466-503a-a8a3-3909c7c30eb3")]
    public readonly InputSlot<SceneSetup> Scene = new();

    [Input(Guid = "d1658e14-8cc0-57ad-8b2e-d98324d90762")]
    public readonly InputSlot<int> PrimitiveIndex = new();

    [Output(Guid = "f5d218bb-d055-5800-9971-db0f88b6ead3", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<Texture2D> Albedo = new();

    [Output(Guid = "26556e6e-caed-5dff-9266-8665065977c2", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<Texture2D> Normal = new();

    [Output(Guid = "6ee9ad33-d30e-5592-bab6-c133054fc554", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<Texture2D> Rmo = new();

    [Output(Guid = "9407cab1-76f5-5e92-af05-0bd3cb06820b", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<Texture2D> Emissive = new();

    private readonly ShaderResourceView?[] _views = new ShaderResourceView?[4];
    private readonly Texture2D?[] _textures = new Texture2D?[4];

    public BlenderTextureSelect()
    {
        Albedo.UpdateAction = Update;
        Normal.UpdateAction = Update;
        Rmo.UpdateAction = Update;
        Emissive.UpdateAction = Update;
    }

    private void Update(EvaluationContext context)
    {
        var scene = Scene.GetValue(context);
        var index = PrimitiveIndex.GetValue(context);
        var material = scene != null && index >= 0 && index < scene.Dispatches.Count
                           ? scene.Dispatches[index].Material : null;
        Albedo.Value = GetTexture(0, material?.AlbedoMapSrv)!;
        Normal.Value = GetTexture(1, material?.NormalSrv)!;
        Rmo.Value = GetTexture(2, material?.RoughnessMetallicOcclusionSrv)!;
        Emissive.Value = GetTexture(3, material?.EmissiveMapSrv)!;
    }

    private Texture2D? GetTexture(int map, ShaderResourceView? view)
    {
        if (ReferenceEquals(_views[map], view) && _textures[map] is { IsDisposed: false })
            return _textures[map];
        _textures[map]?.Dispose();
        _textures[map] = null;
        _views[map] = view;
        if (view == null || view.IsDisposed)
            return null;
        SharpDX.Direct3D11.Resource? resource = null;
        try
        {
            resource = view.Resource;
            var dxTexture = resource?.QueryInterface<SharpDX.Direct3D11.Texture2D>();
            if (dxTexture != null)
                _textures[map] = new Texture2D(dxTexture);
        }
        catch (SharpDX.SharpDXException)
        {
            _textures[map] = null;
        }
        finally
        {
            resource?.Dispose();
        }
        return _textures[map];
    }
}
