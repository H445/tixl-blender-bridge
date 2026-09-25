#nullable enable
using System;
using SharpDX.Direct3D11;
using T3.Core.DataTypes;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Slots;
using T3.Core.Rendering.Material;
using T3.Core.Resource;

namespace PrismalLabs.BlenderExport;

/// <summary>Applies edited texture maps to one primitive, retaining its Blender PBR values.</summary>
[Guid("c25f4c1c-e88d-575e-b8a0-befcf44f208c")]
public sealed class BlenderTextureReplace : Instance<BlenderTextureReplace>
{
    [Input(Guid = "a572804f-65b0-5bb6-b17f-207198bc6867")]
    public readonly InputSlot<SceneSetup> Scene = new();
    [Input(Guid = "233f4c81-bbba-530f-b3fc-604bf1d5a590")]
    public readonly InputSlot<int> PrimitiveIndex = new();
    [Input(Guid = "7ea5475c-6fc4-501b-a9b0-7def755c898b")]
    public readonly InputSlot<Texture2D> Albedo = new();
    [Input(Guid = "d3a68120-5d29-5e2c-b556-0b0ba0c86d97")]
    public readonly InputSlot<Texture2D> Normal = new();
    [Input(Guid = "b30a4fb2-1ce9-5bad-985c-4eff20474ba7")]
    public readonly InputSlot<Texture2D> Rmo = new();
    [Input(Guid = "1cedc4e7-eee9-5690-a7e4-55fb5f73b00f")]
    public readonly InputSlot<Texture2D> Emissive = new();

    [Output(Guid = "8d7ee90b-d479-5c83-9a76-3e1bb0b76143", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<SceneSetup> Result = new();

    private readonly SceneSetup _result = new();
    private PbrMaterial? _sourceMaterial;
    private EditedMaterial? _editedMaterial;
    private readonly Texture2D?[] _maps = new Texture2D?[4];

    public BlenderTextureReplace() => Result.UpdateAction = Update;

    private void Update(EvaluationContext context)
    {
        var scene = Scene.GetValue(context);
        var index = PrimitiveIndex.GetValue(context);
        if (scene == null || index < 0 || index >= scene.Dispatches.Count
            || scene.Dispatches[index].Material == null)
        {
            Result.Value = scene!;
            return;
        }
        var original = scene.Dispatches[index].Material;
        var maps = new[] { Albedo.GetValue(context), Normal.GetValue(context),
                           Rmo.GetValue(context), Emissive.GetValue(context) };
        if (Array.TrueForAll(maps, map => map == null || map.IsDisposed))
        {
            Result.Value = scene;
            return;
        }
        var changed = !ReferenceEquals(original, _sourceMaterial) || _editedMaterial == null;
        for (var i = 0; i < maps.Length; i++)
            changed |= !ReferenceEquals(maps[i], _maps[i]);
        if (changed)
        {
            _editedMaterial?.Dispose();
            _editedMaterial = new EditedMaterial(original, maps);
            _sourceMaterial = original;
            Array.Copy(maps, _maps, maps.Length);
        }
        else
        {
            _editedMaterial!.Parameters = original.Parameters;
            _editedMaterial.UpdateParameterBuffer();
        }

        _result.Dispatches.Clear();
        for (var i = 0; i < scene.Dispatches.Count; i++)
        {
            var dispatch = scene.Dispatches[i];
            if (i != index)
            {
                _result.Dispatches.Add(dispatch);
                continue;
            }
            _result.Dispatches.Add(new SceneSetup.SceneDrawDispatch
            {
                MeshBuffers = dispatch.MeshBuffers,
                VertexCount = dispatch.VertexCount,
                VertexStartIndex = dispatch.VertexStartIndex,
                Material = _editedMaterial,
                CombinedTransform = dispatch.CombinedTransform,
                ChunkIndex = dispatch.ChunkIndex,
                Scale = dispatch.Scale,
                SkinWeights = dispatch.SkinWeights,
                SkeletonIndex = dispatch.SkeletonIndex,
            });
        }
        Result.Value = _result;
    }

    private sealed class EditedMaterial : PbrMaterial
    {
        private readonly ShaderResourceView?[] _owned = new ShaderResourceView?[4];
        private bool _disposed;

        public EditedMaterial(PbrMaterial source, Texture2D?[] maps)
        {
            Name = source.Name;
            Parameters = source.Parameters;
            AlbedoMapSrv = View(maps[0], source.AlbedoMapSrv, 0);
            NormalSrv = View(maps[1], source.NormalSrv, 1);
            RoughnessMetallicOcclusionSrv = View(maps[2], source.RoughnessMetallicOcclusionSrv, 2);
            EmissiveMapSrv = View(maps[3], source.EmissiveMapSrv, 3);
            UpdateParameterBuffer();
        }

        private ShaderResourceView View(Texture2D? texture, ShaderResourceView fallback, int index)
        {
            if (texture == null || texture.IsDisposed)
                return fallback;
            _owned[index] = new ShaderResourceView(ResourceManager.Device, texture);
            return _owned[index]!;
        }

        protected override void Dispose(bool disposing)
        {
            if (!disposing || _disposed)
                return;
            _disposed = true;
            foreach (var view in _owned)
                view?.Dispose();
            ParameterBuffer?.Dispose();
            ParameterBuffer = null;
        }
    }
}
